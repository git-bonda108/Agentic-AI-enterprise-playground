"""Knowledge Q&A: retrieval over policy documents, a cited answer, and a citation check."""

from __future__ import annotations

import re

from langgraph.graph import END, START, StateGraph

from app.agents.core import Blueprint, RunState, register, step
from app.agents.data import load_json
from app.agents.runtime import ctx_from_config

STOP = {"the", "and", "for", "what", "is", "are", "of", "a", "an", "to", "in", "on", "per", "how", "much", "can", "i", "my", "our"}


def _terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 2}


def retrieve(state: RunState, config) -> dict:
    question = state["input"].get("question", "")
    space_id = state["input"].get("space_id")
    if space_id:
        from app.db import SessionLocal
        from app.knowledge import search
        from app.models import KnowledgeSpace

        with SessionLocal() as db:
            space = db.get(KnowledgeSpace, space_id)
            hits = search(db, space, question, k=4) if space else []
        top = [{"id": h["cite"], "title": h["title"], "body": h["text"], "score": h["score"]} for h in hits]
        return {"data": {"question": question, "retrieved": top, "space": space.name if space else None}, **step(state, "retrieve", f"Retrieved {len(top)} chunks from Knowledge Space '{space.name if space else space_id}'", {"scores": {t["id"]: t["score"] for t in top}})}
    q = _terms(question)
    scored = []
    for doc in load_json("policies.json"):
        body = _terms(doc["title"] + " " + doc["body"])
        overlap = len(q & body)
        title_bonus = len(q & _terms(doc["title"])) * 2
        scored.append((overlap + title_bonus, doc))
    scored.sort(key=lambda x: -x[0])
    top = [{"id": d["id"], "title": d["title"], "body": d["body"], "score": s} for s, d in scored[:3] if s > 0] or [{"id": d["id"], "title": d["title"], "body": d["body"], "score": 0} for _, d in scored[:1]]
    return {"data": {"question": question, "retrieved": top}, **step(state, "retrieve", f"Retrieved {len(top)} policies: {', '.join(t['id'] for t in top)}", {"scores": {t['id']: t['score'] for t in top}})}


def answer(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    d = state["data"]
    context = "\n\n".join(f"[{t['id']}] {t['title']}: {t['body']}" for t in d["retrieved"])
    ids = ", ".join(f"[{t['id']}]" for t in d["retrieved"][:3]) or "[POL-001]"
    text = ctx.llm("Workhorse", f"Answer using only the excerpts provided. Cite the source id in square brackets after each claim, exactly as given, for example {ids}. If the excerpts do not answer the question, say so.", f"Question: {d['question']}\n\nExcerpts:\n{context}")
    return {"data": {**d, "answer": text}, **step(state, "answer", "Drafted a cited answer", kind="llm")}


def verify(state: RunState, config) -> dict:
    d = state["data"]
    known = {t["id"] for t in d["retrieved"]}
    cited = {k for k in known if f"[{k}]" in d["answer"]} | set(re.findall(r"POL-\d{3}", d["answer"]))
    invalid = sorted(cited - known)
    answer_text = d["answer"]
    if not cited & known:
        answer_text += "\n\nSources: " + ", ".join(f"[{t['id']}] {t['title']}" for t in d["retrieved"])
    citations = sorted((cited & known) or known)
    output = {"answer_md": answer_text, "citations": citations, "invalid_citations": invalid, "retrieved": [{"id": t["id"], "title": t["title"], "score": t["score"]} for t in d["retrieved"]], "grounded": not invalid}
    return {"output": output, **step(state, "verify", f"Citation check: {len(citations)} valid, {len(invalid)} invalid", kind="gate")}


def build(checkpointer):
    g = StateGraph(RunState)
    for name, fn in (("retrieve", retrieve), ("answer", answer), ("verify", verify)):
        g.add_node(name, fn)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "answer")
    g.add_edge("answer", "verify")
    g.add_edge("verify", END)
    return g.compile(checkpointer=checkpointer)


register(Blueprint(
    id="knowledge-qa", name="Knowledge Q&A", family="Domain", pattern="Retrieve, answer with citations, verify",
    summary="Grounded answers with citations over your policy documents, with every citation checked.",
    description="Retrieval selects the top passages (hybrid vector and keyword search over a Knowledge Space, or lexical over the policy set), the model answers with inline citations, and a verifier rejects citations that were not retrieved.",
    tiers={"retrieve": "deterministic", "answer": "Workhorse", "verify": "deterministic"},
    graph={"nodes": [{"id": "retrieve", "label": "Retrieve policies", "kind": "tool"}, {"id": "answer", "label": "Answer with citations", "kind": "llm"}, {"id": "verify", "label": "Verify citations", "kind": "gate"}], "edges": [["retrieve", "answer"], ["answer", "verify"]], "columns": [["retrieve"], ["answer"], ["verify"]]},
    samples=[{"name": "Hotel limit", "input": {"question": "What is the hotel limit per night when travelling?"}}, {"name": "Large purchase", "input": {"question": "What do I need for a purchase over 50,000 USD?"}}, {"name": "AI and restricted data", "input": {"question": "Can I paste payroll data into an external AI tool?"}}],
    datasets=["policies"], flavors=["LangGraph", "Google ADK", "Strands"],
    review_gates=[], dashboard=["Questions", "Grounded rate", "Invalid citations"],
    links={"origin": "https://github.com/git-bonda108/conversational-rag-assistant"},
    build=build, input_schema={"question": "text", "space_id": "optional Knowledge Space id"},
))
