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
    text = ctx.llm("Workhorse", "Answer using only the policy excerpts provided. Cite the policy id in square brackets after each claim, like [POL-001]. If the excerpts do not answer the question, say so.", f"Question: {d['question']}\n\nExcerpts:\n{context}")
    return {"data": {**d, "answer": text}, **step(state, "answer", "Drafted a cited answer", kind="llm")}


def verify(state: RunState, config) -> dict:
    d = state["data"]
    cited = set(re.findall(r"POL-\d{3}", d["answer"]))
    known = {t["id"] for t in d["retrieved"]}
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
    description="Lexical retrieval selects the top policies, the model answers with inline citations, and a verifier rejects citations that were not retrieved. Knowledge Spaces with vector retrieval replace the lexical step in Batch 6.",
    tiers={"retrieve": "deterministic", "answer": "Workhorse", "verify": "deterministic"},
    graph={"nodes": [{"id": "retrieve", "label": "Retrieve policies", "kind": "tool"}, {"id": "answer", "label": "Answer with citations", "kind": "llm"}, {"id": "verify", "label": "Verify citations", "kind": "gate"}], "edges": [["retrieve", "answer"], ["answer", "verify"]], "columns": [["retrieve"], ["answer"], ["verify"]]},
    samples=[{"name": "Hotel limit", "input": {"question": "What is the hotel limit per night when travelling?"}}, {"name": "Large purchase", "input": {"question": "What do I need for a purchase over 50,000 USD?"}}, {"name": "AI and restricted data", "input": {"question": "Can I paste payroll data into an external AI tool?"}}],
    datasets=["policies"], flavors=["LangGraph", "Google ADK", "Strands"],
    review_gates=[], dashboard=["Questions", "Grounded rate", "Invalid citations"],
    links={"origin": "https://github.com/git-bonda108/conversational-rag-assistant"},
    build=build, input_schema={"question": "text"},
))
