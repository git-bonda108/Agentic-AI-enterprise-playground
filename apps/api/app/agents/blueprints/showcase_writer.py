"""Showcase writer: a platform agent that drafts a showcase post (title, summary, outcome, tags) from a run or a description."""

from __future__ import annotations

import re

from langgraph.graph import END, START, StateGraph

from app.agents.core import Blueprint, RunState, parse_json, register, step
from app.agents.runtime import ctx_from_config
from app.db import SessionLocal
from app.models import Run

TAG_WORDS = {"invoice": "finance", "reconcil": "finance", "policy": "policies", "travel": "hr", "learning": "learning", "research": "research", "contract": "legal", "review": "quality", "canary": "reliability", "eval": "quality", "knowledge": "knowledge", "graph": "engineering", "sql": "data", "dashboard": "data", "model": "models", "compare": "models"}


def collect(state: RunState, config) -> dict:
    inp = state["input"]
    text = str(inp.get("text") or "").strip()
    source = "text"
    if inp.get("run_id"):
        with SessionLocal() as db:
            run = db.get(Run, str(inp["run_id"]))
        if run is not None:
            out = run.output or {}
            body = str(out.get("answer_md") or out.get("summary_md") or out.get("path_md") or out)[:2500]
            text = f"Agent {run.blueprint_id} run {run.id[:8]}: input {run.input}. Result: {body}"
            source = f"run:{run.id}"
    if not text:
        text = "A playground result worth sharing."
    tags = sorted({v for k, v in TAG_WORDS.items() if k in text.lower()})[:5]
    return {"data": {"text": text, "source": source, "tags": tags}, **step(state, "collect", f"Collected material from {source} ({len(text)} chars)", {"tags": tags})}


def draft(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    d = state["data"]
    raw = ctx.llm("Economy", "You write short showcase posts for colleagues. Return JSON only: {\"title\": <8 words max>, \"summary\": <2 sentences, plain>, \"outcome\": <one line with the business result>, \"tags\": [<up to 5 lowercase tags>]}.", d["text"], json_mode=True, max_tokens=300)
    parsed = parse_json(raw, None)
    if not isinstance(parsed, dict) or not parsed.get("title"):
        first = re.split(r"[.!?]", d["text"])[0].strip()
        parsed = {"title": (first[:60] or "A result worth sharing"), "summary": d["text"][:240], "outcome": first[:120], "tags": d["tags"] or ["playground"]}
    tags = [str(t).lower()[:24] for t in (parsed.get("tags") or [])][:5] or d["tags"] or ["playground"]
    output = {"title": str(parsed.get("title", ""))[:140], "summary": str(parsed.get("summary", ""))[:600], "outcome": str(parsed.get("outcome", ""))[:300], "tags": tags, "source": d["source"]}
    return {"output": output, **step(state, "draft", f"Drafted '{output['title']}' with {len(tags)} tags", kind="llm")}


def build(checkpointer):
    g = StateGraph(RunState)
    g.add_node("collect", collect)
    g.add_node("draft", draft)
    g.add_edge(START, "collect")
    g.add_edge("collect", "draft")
    g.add_edge("draft", END)
    return g.compile(checkpointer=checkpointer)


register(Blueprint(
    id="showcase-writer", name="Showcase writer", family="Platform", pattern="Collect, draft",
    summary="Drafts a showcase post from a run or a sentence, so sharing a win takes one click.",
    description="A platform agent: reads a run's input and result (or free text), then drafts a title, a two-sentence summary, a one-line business outcome and tags.",
    tiers={"collect": "deterministic", "draft": "Economy"},
    graph={"nodes": [{"id": "collect", "label": "Collect material", "kind": "tool"}, {"id": "draft", "label": "Draft the post", "kind": "llm"}], "edges": [["collect", "draft"]], "columns": [["collect"], ["draft"]]},
    samples=[{"name": "From a sentence", "input": {"text": "Reconciled 24 invoices against purchase orders and flagged 6 for review."}}],
    datasets=[], flavors=["LangGraph"], review_gates=[], dashboard=["Posts drafted"], links={"origin": "/community/showcase"},
    build=build, input_schema={"run_id": "optional run id", "text": "optional description"}, batch=8,
))
