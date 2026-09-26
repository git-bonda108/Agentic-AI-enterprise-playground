"""Onboarding coach: a platform agent that reads a person's own ledger and suggests their next three steps in the playground."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from langgraph.graph import END, START, StateGraph
from sqlalchemy import func, select

from app.agents.core import Blueprint, RunState, parse_json, register, step
from app.agents.runtime import ctx_from_config
from app.db import SessionLocal

JOURNEY = [
    ("chat", "Playground", "/build/playground", "Ask a model in the Playground and watch the cost per message"),
    ("compare", "Compare models", "/build/playground", "Compare two models on the same prompt"),
    ("notebook", "Notebooks", "/build/notebooks", "Run the Hello notebook end to end"),
    ("agent", "Agent Hub", "/build/agents", "Run a blueprint and answer its review gate"),
    ("knowledge", "Knowledge", "/build/knowledge", "Create a Knowledge Space from a document and ask it a question"),
    ("eval", "Evaluate", "/evaluate/evals", "Turn a good run into an evaluation suite"),
    ("sdk", "Frameworks", "/discover/frameworks", "Point your own SDK at the playground gateway"),
]


def observe(state: RunState, config) -> dict:
    from app.models import UsageEvent, User

    ctx = ctx_from_config(config)
    target = state["input"].get("user_id") or ctx.user_id
    days = int(state["input"].get("days") or 30)
    since = datetime.now(UTC) - timedelta(days=days)
    with SessionLocal() as db:
        me = db.get(User, ctx.user_id)
        if target != ctx.user_id and (me is None or me.role not in ("admin", "champion")):
            target = ctx.user_id
        person = db.get(User, target)
        rows = db.execute(select(UsageEvent.feature, func.count(), func.sum(UsageEvent.cost_usd)).where(UsageEvent.user_id == target, UsageEvent.created_at >= since).group_by(UsageEvent.feature)).all()
    used = {f: {"calls": int(n), "cost_usd": round(float(c or 0), 4)} for f, n, c in rows}
    unused = [j for j in JOURNEY if j[0] not in used]
    return {"data": {"user": {"id": target, "name": person.name if person else target, "role": person.role if person else "explorer", "department": person.department if person else ""}, "days": days, "used": used, "unused": [{"feature": f, "page": p, "href": h, "task": t} for f, p, h, t in unused]}, **step(state, "observe", f"{len(used)} features used in {days} days; {len(unused)} not yet", {"used": list(used)})}


def coach(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    d = state["data"]
    raw = ctx.llm("Economy", "You coach a colleague on getting value from an enterprise AI playground. Return JSON: {\"note_md\": str, \"next_steps\": [{\"page\": str, \"href\": str, \"task\": str, \"why\": str}]} with at most three next steps chosen from the unused features, ordered from easiest to most valuable for their role. Warm, specific, under 120 words.", f"Person: {d['user']}. Used in the last {d['days']} days: {d['used']}. Not yet used: {d['unused']}", json_mode=True, max_tokens=500)
    parsed = parse_json(raw, None)
    steps = parsed.get("next_steps") if isinstance(parsed, dict) else None
    note = parsed.get("note_md") if isinstance(parsed, dict) else None
    if not isinstance(steps, list) or not steps:
        steps = [{"page": u["page"], "href": u["href"], "task": u["task"], "why": "The next thing most people find useful"} for u in d["unused"][:3]]
    if not note:
        note = f"You have used {len(d['used'])} of {len(JOURNEY)} features in {d['days']} days. Three next steps are below."
    output = {"note_md": note, "next_steps": [{"page": str(s.get("page", "")), "href": str(s.get("href", "/home")), "task": str(s.get("task", "")), "why": str(s.get("why", ""))} for s in steps][:3], "used": d["used"], "person": d["user"]["name"]}
    return {"output": output, **step(state, "coach", f"Suggested {len(output['next_steps'])} next steps", kind="llm")}


def build(checkpointer):
    g = StateGraph(RunState)
    g.add_node("observe", observe)
    g.add_node("coach", coach)
    g.add_edge(START, "observe")
    g.add_edge("observe", "coach")
    g.add_edge("coach", END)
    return g.compile(checkpointer=checkpointer)


register(Blueprint(
    id="onboarding-coach", name="Onboarding coach", family="Platform", pattern="Observe usage, suggest the next steps",
    summary="Reads what a person has used in the playground and suggests their next three steps, with the page to open and why.",
    description="A platform agent that turns the ledger into coaching: which features a person has used in the last 30 days, which they have not, and three next steps ordered from easiest to most valuable for their role. Admins and champions can run it for a colleague.",
    tiers={"observe": "deterministic", "coach": "Economy"},
    graph={"nodes": [{"id": "observe", "label": "Observe usage", "kind": "tool"}, {"id": "coach", "label": "Suggest next steps", "kind": "llm"}], "edges": [["observe", "coach"]], "columns": [["observe"], ["coach"]]},
    samples=[{"name": "Coach me", "input": {"days": 30}}],
    datasets=[], flavors=["LangGraph"], review_gates=[], dashboard=["People coached", "Steps followed"], links={"origin": "/operate/adoption"},
    build=build, input_schema={"days": "integer, default 30", "user_id": "optional, admins and champions only"}, batch=14,
))
