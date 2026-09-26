"""Connector reviewer: a platform agent that prepares the admin's approval queue for the MCP Marketplace."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select

from app.agents.core import Blueprint, RunState, parse_json, register, step
from app.agents.runtime import ctx_from_config
from app.db import SessionLocal


def shortlist(state: RunState, config) -> dict:
    from app.lowcode import NOISY_PUBLISHERS, VENDOR_PUBLISHERS
    from app.models import Connector

    limit = int(state["input"].get("limit") or 12)
    with SessionLocal() as db:
        pending = db.scalars(select(Connector).where(Connector.approval == "pending").order_by(Connector.signals.desc(), Connector.title)).all()
    rows = []
    for c in pending:
        if (c.publisher or "") in NOISY_PUBLISHERS:
            continue
        vendor = (c.publisher or "") in VENDOR_PUBLISHERS or not (c.publisher or "").startswith("io.github")
        score = (c.signals or 0) + (3 if vendor else 0) + (1 if c.transport == "remote" else 0)
        rows.append({"id": c.id, "title": c.title, "publisher": c.publisher, "transport": c.transport, "signals": c.signals, "vendor": vendor, "category": c.category, "env_vars": c.env_vars or [], "description": (c.description or "")[:200], "score": score})
    rows.sort(key=lambda r: (-r["score"], r["title"]))
    top = rows[:limit]
    return {"data": {"candidates": top, "pending_total": len(pending)}, **step(state, "shortlist", f"Shortlisted {len(top)} of {len(pending)} pending servers by signals, publisher and transport", {"ids": [r["id"] for r in top]})}


def recommend(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    d = state["data"]
    raw = ctx.llm("Economy", "You advise an enterprise admin on which MCP servers to approve. For each candidate return JSON: {\"reviews\": [{\"id\": str, \"decision\": \"approve\"|\"hold\"|\"block\", \"reason\": str}]}. Approve vendor-published remote servers with clear purpose; hold community servers that need secrets until their repository is reviewed; block anything that resells access or is unrelated to business work. Use only the facts given.", f"Candidates: {d['candidates']}", json_mode=True, max_tokens=900)
    parsed = parse_json(raw, None)
    reviews = parsed.get("reviews") if isinstance(parsed, dict) else None
    by_id = {r.get("id"): r for r in reviews} if isinstance(reviews, list) else {}
    out_rows = []
    for c in d["candidates"]:
        r = by_id.get(c["id"]) or {"decision": "approve" if c["vendor"] and c["transport"] == "remote" else "hold", "reason": "Vendor-published remote server" if c["vendor"] and c["transport"] == "remote" else "Community server; review the repository and the secrets it needs before approving"}
        out_rows.append({**c, "decision": r.get("decision", "hold"), "reason": str(r.get("reason", ""))[:240]})
    counts = {k: sum(1 for r in out_rows if r["decision"] == k) for k in ("approve", "hold", "block")}
    output = {"reviews": out_rows, "counts": counts, "pending_total": d["pending_total"], "summary_md": f"Reviewed {len(out_rows)} of {d['pending_total']} pending servers: {counts['approve']} to approve, {counts['hold']} to hold, {counts['block']} to block. Decide in the MCP Marketplace."}
    return {"output": output, **step(state, "recommend", f"{counts['approve']} approve · {counts['hold']} hold · {counts['block']} block", kind="llm")}


def build(checkpointer):
    g = StateGraph(RunState)
    g.add_node("shortlist", shortlist)
    g.add_node("recommend", recommend)
    g.add_edge(START, "shortlist")
    g.add_edge("shortlist", "recommend")
    g.add_edge("recommend", END)
    return g.compile(checkpointer=checkpointer)


register(Blueprint(
    id="connector-reviewer", name="Connector reviewer", family="Platform", pattern="Shortlist, recommend a decision per item",
    summary="Prepares the MCP approval queue: shortlists pending servers by signals, publisher and transport and recommends approve, hold or block with a reason.",
    description="A platform agent for admins: ranks pending marketplace servers (vendor publishers and remote transports first, resellers excluded), asks a model for a decision and a one-line reason per server using only the registry facts, and returns a queue the admin can act on in the MCP Marketplace.",
    tiers={"shortlist": "deterministic", "recommend": "Economy"},
    graph={"nodes": [{"id": "shortlist", "label": "Shortlist pending servers", "kind": "tool"}, {"id": "recommend", "label": "Recommend decisions", "kind": "llm"}], "edges": [["shortlist", "recommend"]], "columns": [["shortlist"], ["recommend"]]},
    samples=[{"name": "Top 12 pending", "input": {"limit": 12}}, {"name": "Top 5", "input": {"limit": 5}}],
    datasets=[], flavors=["LangGraph"], review_gates=[], dashboard=["Reviewed", "Approved"], links={"origin": "/discover/connectors"},
    build=build, input_schema={"limit": "integer, default 12"}, batch=14,
))
