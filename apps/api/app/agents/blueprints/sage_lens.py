"""Sage Lens deep research: clarity gate, research with a validator loop, and a sourced synthesis."""

from __future__ import annotations

import logging
import os
import re

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents.core import Blueprint, RunState, register, step
from app.agents.data import load_json
from app.agents.runtime import ctx_from_config

logger = logging.getLogger("playground.sage_lens")
MAX_ATTEMPTS = 3
STOPWORDS = {"what", "does", "the", "and", "for", "with", "how", "about", "tell", "me", "is", "are", "of", "a", "an", "to", "in", "on"}


def _detect_company(text: str, corpus: dict) -> str | None:
    low = text.lower()
    for name in corpus:
        if name.lower() in low:
            return name
    return None


def clarity(state: RunState, config) -> dict:
    corpus = load_json("research_corpus.json")
    question = state["input"].get("question", "").strip()
    company = state["input"].get("company") or _detect_company(question, corpus)
    if company is None:
        answer = interrupt({"question": "Which company or topic should I research?", "options": list(corpus.keys()), "free_text": "Or name another company", "context": question})
        chosen = answer.get("decision") if isinstance(answer, dict) else str(answer)
        company = _detect_company(str(chosen), corpus) or str(chosen)
        question = question or f"Tell me about {company}"
        rec = step(state, "clarity", f"Clarified with the user: {company}", kind="human")
    else:
        rec = step(state, "clarity", f"Question is clear; subject: {company}", kind="gate")
    return {"data": {**state.get("data", {}), "company": company, "question": question, "attempts": 0, "findings": []}, **rec}


def research(state: RunState, config) -> dict:
    d = state["data"]
    corpus = load_json("research_corpus.json")
    attempts = d["attempts"] + 1
    findings = [{"text": t, "source": s} for t, s in corpus.get(d["company"], [])]
    if not findings:
        findings = [{"text": f"No offline facts for {d['company']}; the live search connector is not configured.", "source": ""}]
    live = False
    if os.environ.get("TAVILY_API_KEY") and attempts > 1:
        try:
            import httpx

            r = httpx.post("https://api.tavily.com/search", json={"api_key": os.environ["TAVILY_API_KEY"], "query": d["question"], "max_results": 5}, timeout=20)
            for item in r.json().get("results", []):
                findings.append({"text": item.get("content", "")[:400], "source": item.get("url", "")})
            live = True
        except (OSError, ValueError, KeyError) as exc:  # keep the offline findings
            logger.warning("live search failed: %s", exc)
    return {"data": {**d, "attempts": attempts, "findings": findings, "live": live}, **step(state, "research", f"Attempt {attempts}: {len(findings)} findings{' (offline corpus)' if not live else ' (offline + live search)'}")}


def validate(state: RunState, config) -> dict:
    d = state["data"]
    terms = [w for w in re.findall(r"[a-z]+", d["question"].lower()) if w not in STOPWORDS and len(w) > 3]
    text = " ".join(f["text"].lower() for f in d["findings"])
    covered = [t for t in terms if t in text]
    sufficient = len(d["findings"]) >= 3 and (not terms or covered or d["attempts"] >= MAX_ATTEMPTS)
    confidence = round(min(1.0, len(d["findings"]) / 4 + (len(covered) / max(len(terms), 1)) * 0.3), 2)
    return {"data": {**d, "sufficient": sufficient, "confidence": confidence, "covered": covered}, **step(state, "validate", f"Coverage {len(covered)}/{len(terms)} terms, {len(d['findings'])} findings, confidence {confidence}: {'sufficient' if sufficient else 'needs another pass'}", kind="gate")}


def route_after_validate(state: RunState) -> str:
    d = state["data"]
    return "synthesize" if d["sufficient"] or d["attempts"] >= MAX_ATTEMPTS else "research"


def synthesize(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    d = state["data"]
    facts = "\n".join(f"- {f['text']} (source: {f['source'] or 'offline corpus'})" for f in d["findings"])
    answer = ctx.llm("Workhorse", "You are a research analyst. Answer the question using only the findings provided, cite sources inline as [n], and finish with a 'Sources' list. Use markdown.", f"Question: {d['question']}\nSubject: {d['company']}\nFindings:\n{facts}")
    output = {"answer_md": answer, "company": d["company"], "sources": [f["source"] for f in d["findings"] if f["source"]], "attempts": d["attempts"], "confidence": d["confidence"], "live_search": d.get("live", False)}
    return {"output": output, **step(state, "synthesize", f"Synthesized an answer from {len(d['findings'])} findings", kind="llm")}


def build(checkpointer):
    g = StateGraph(RunState)
    g.add_node("clarity", clarity)
    g.add_node("research", research)
    g.add_node("validate", validate)
    g.add_node("synthesize", synthesize)
    g.add_edge(START, "clarity")
    g.add_edge("clarity", "research")
    g.add_edge("research", "validate")
    g.add_conditional_edges("validate", route_after_validate, {"synthesize": "synthesize", "research": "research"})
    g.add_edge("synthesize", END)
    return g.compile(checkpointer=checkpointer)


register(Blueprint(
    id="sage-lens", name="Sage Lens deep research", family="Domain", pattern="Clarity gate, research, validator loop, synthesis",
    summary="Sourced research with a validator loop and a human clarification when the question is vague.",
    description="A clarity node checks the question names a subject and interrupts for clarification if not. Research gathers findings from an offline corpus and, when a search key is configured, live web results. A validator scores coverage and sends the graph back for another pass up to three times. Synthesis writes a cited answer.",
    tiers={"clarity": "deterministic", "research": "tool", "validate": "deterministic", "synthesize": "Workhorse"},
    graph={"nodes": [{"id": "clarity", "label": "Clarity gate", "kind": "human"}, {"id": "research", "label": "Research", "kind": "tool"}, {"id": "validate", "label": "Validate coverage", "kind": "gate"}, {"id": "synthesize", "label": "Synthesize", "kind": "llm"}], "edges": [["clarity", "research"], ["research", "validate"], ["validate", "synthesize"], ["validate", "research", "retry"]], "columns": [["clarity"], ["research"], ["validate"], ["synthesize"]]},
    samples=[{"name": "Clear question about Tesla", "input": {"question": "What does Tesla sell and where does it build vehicles?"}}, {"name": "Vague question (asks you to clarify)", "input": {"question": "Give me an overview"}}, {"name": "Microsoft and AI", "input": {"question": "How does Microsoft sell AI models and Copilot to enterprises?"}}],
    datasets=["research_corpus"], flavors=["LangGraph", "Google ADK", "Claude"],
    review_gates=["Vague questions pause for clarification"], dashboard=["Runs", "Clarifications", "Average attempts", "Confidence"],
    links={"pattern": "https://docs.langchain.com/oss/python/langgraph/interrupts", "origin": "https://github.com/git-bonda108/deep-research-agent-langgraph"},
    build=build, input_schema={"question": "text", "company": "optional subject"},
))
