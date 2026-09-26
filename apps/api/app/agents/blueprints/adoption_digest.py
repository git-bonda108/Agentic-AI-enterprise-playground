"""Adoption digest: a platform agent that turns the adoption analytics into a narrative for leaders, with recommendations."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.core import Blueprint, RunState, parse_json, register, step
from app.agents.runtime import ctx_from_config
from app.db import SessionLocal


def gather(state: RunState, config) -> dict:
    from app.adoption import summary

    inp = state["input"]
    days = int(inp.get("days") or 7)
    with SessionLocal() as db:
        data = summary(db, days=max(1, min(days, 365)), department=inp.get("department") or None)
    top = data["features"][:3]
    return {"data": {"days": days, "audience": inp.get("audience", "team leads"), "summary": data, "top_features": [f["label"] for f in top]}, **step(state, "gather", f"Aggregated {data['kpis']['outcomes']} outcomes across {data['kpis']['active_users']} active people over {days} days", {"kpis": data["kpis"]})}


def narrate(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    d = state["data"]
    s = d["summary"]
    facts = {
        "days": d["days"], "kpis": s["kpis"], "features": [{k: f[k] for k in ("label", "hours", "outcomes", "cost_usd", "hours_saved", "users")} for f in s["features"][:6]],
        "departments": [{k: r[k] for k in ("department", "users", "hours", "outcomes", "cost_usd", "hours_saved", "roi")} for r in s["departments"][:8]], "method": s["method"],
    }
    text = ctx.llm("Workhorse", f"You write short, honest adoption digests for {d['audience']}. Use only the numbers given. Mark estimates as estimates. Markdown, at most 220 words, with headings 'Headline', 'What people used', 'Where value showed up', 'Watch-outs'.", f"Facts:\n{facts}", max_tokens=700)
    return {"data": {**d, "digest": text}, **step(state, "narrate", f"Wrote a {len(text.split())}-word digest", kind="llm")}


def recommend(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    d = state["data"]
    raw = ctx.llm("Economy", "Return JSON: {\"recommendations\": [{\"action\": str, \"why\": str, \"owner\": str}]} with three concrete actions to raise adoption or cut cost, based only on the digest.", d["digest"], json_mode=True, max_tokens=400)
    parsed = parse_json(raw, None)
    recs = parsed.get("recommendations") if isinstance(parsed, dict) else None
    if not isinstance(recs, list) or not recs:
        recs = [{"action": "Run a 30-minute clinic for the least active department", "why": "Adoption follows the first successful task", "owner": "AI champion"}, {"action": "Turn the most used conversation into a wizard agent", "why": "Repeatable tasks belong in agents", "owner": "Builder"}, {"action": "Enable Smart routing by default for explorers", "why": "Cuts cost without changing outcomes", "owner": "Admin"}]
    output = {"digest_md": d["digest"], "kpis": d["summary"]["kpis"], "top_features": d["top_features"], "recommendations": recs[:5], "days": d["days"], "assumptions": d["summary"]["assumptions"]}
    return {"output": output, **step(state, "recommend", f"{len(recs[:5])} recommendations", kind="llm")}


def build(checkpointer):
    g = StateGraph(RunState)
    for name, fn in (("gather", gather), ("narrate", narrate), ("recommend", recommend)):
        g.add_node(name, fn)
    g.add_edge(START, "gather")
    g.add_edge("gather", "narrate")
    g.add_edge("narrate", "recommend")
    g.add_edge("recommend", END)
    return g.compile(checkpointer=checkpointer)


register(Blueprint(
    id="adoption-digest", name="Adoption digest", family="Platform", pattern="Aggregate, narrate, recommend",
    summary="Turns the adoption analytics into a short digest with three recommendations. Runs the platform, not a business process.",
    description="A platform agent: aggregates hours per feature, outcomes, cost and estimated value for a window, writes a digest for the chosen audience using only those numbers, and proposes three actions.",
    tiers={"gather": "deterministic", "narrate": "Workhorse", "recommend": "Economy"},
    graph={"nodes": [{"id": "gather", "label": "Aggregate analytics", "kind": "tool"}, {"id": "narrate", "label": "Write the digest", "kind": "llm"}, {"id": "recommend", "label": "Recommend actions", "kind": "llm"}], "edges": [["gather", "narrate"], ["narrate", "recommend"]], "columns": [["gather"], ["narrate"], ["recommend"]]},
    samples=[{"name": "Last 7 days", "input": {"days": 7}}, {"name": "Last 30 days for executives", "input": {"days": 30, "audience": "executives"}}],
    datasets=[], flavors=["LangGraph"], review_gates=[], dashboard=["Digests", "Recommendations adopted"], links={"origin": "/operate/adoption"},
    build=build, input_schema={"days": "integer, default 7", "department": "optional", "audience": "optional"}, batch=8,
))
