"""Cost sentinel: a platform agent that compares the last day's spend with the trailing week and alerts on anomalies."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select

from app.agents.core import Blueprint, RunState, parse_json, register, step
from app.agents.runtime import ctx_from_config
from app.db import SessionLocal


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def measure(state: RunState, config) -> dict:
    from app.models import Alert, UsageEvent, User

    inp = state["input"]
    threshold_pct = float(inp.get("threshold_pct") or 50)
    floor_usd = float(inp.get("floor_usd") or 0.5)
    now = datetime.now(UTC)
    day_ago, week_ago = now - timedelta(days=1), now - timedelta(days=8)
    with SessionLocal() as db:
        events = db.scalars(select(UsageEvent).where(UsageEvent.created_at >= week_ago)).all()
        users = {u.id: u for u in db.scalars(select(User))}
        last: dict[str, float] = {}
        prior: dict[str, float] = {}
        for e in events:
            key = f"{users[e.user_id].department if e.user_id in users else 'Unknown'} · {e.feature}"
            bucket = last if _aware(e.created_at) >= day_ago else prior
            bucket[key] = bucket.get(key, 0.0) + e.cost_usd
        rows = []
        for key in sorted(set(last) | set(prior)):
            baseline = prior.get(key, 0.0) / 7.0
            today = last.get(key, 0.0)
            change = ((today - baseline) / baseline * 100.0) if baseline > 0 else (100.0 if today > 0 else 0.0)
            rows.append({"segment": key, "last_24h_usd": round(today, 4), "daily_baseline_usd": round(baseline, 4), "change_pct": round(change, 1), "anomaly": today >= floor_usd and change >= threshold_pct})
        anomalies = [r for r in rows if r["anomaly"]]
        if anomalies:
            db.add(Alert(scope="cost", key="sentinel", label=f"Spend anomaly in {len(anomalies)} segment(s)", threshold=int(threshold_pct), period=now.strftime("%Y-%m"), spend_usd=sum(a["last_24h_usd"] for a in anomalies), cap_usd=sum(a["daily_baseline_usd"] for a in anomalies), kind="cost", message="; ".join(f"{a['segment']}: ${a['last_24h_usd']:.2f} vs ${a['daily_baseline_usd']:.2f}/day (+{a['change_pct']:.0f}%)" for a in anomalies)[:2000]))
            db.commit()
    total_last = round(sum(r["last_24h_usd"] for r in rows), 4)
    return {"data": {"rows": rows, "anomalies": anomalies, "threshold_pct": threshold_pct, "floor_usd": floor_usd, "total_last_24h": total_last}, **step(state, "measure", f"Compared {len(rows)} department·feature segments; {len(anomalies)} anomalies over {threshold_pct:.0f}%", {"total_last_24h_usd": total_last})}


def explain(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    d = state["data"]
    top = sorted(d["rows"], key=lambda r: -r["last_24h_usd"])[:8]
    raw = ctx.llm("Economy", "Return JSON: {\"summary_md\": str, \"actions\": [str]} for a finance-minded admin. summary_md is at most 120 words and uses only the numbers given; actions are up to three concrete checks (who to ask, which budget to tighten). Estimates must be called estimates.", f"Threshold {d['threshold_pct']}% over a 7-day daily baseline, floor ${d['floor_usd']}. Segments (last 24h vs baseline/day): {top}. Anomalies: {d['anomalies']}", json_mode=True, max_tokens=450)
    parsed = parse_json(raw, None)
    summary = parsed.get("summary_md") if isinstance(parsed, dict) else None
    actions = parsed.get("actions") if isinstance(parsed, dict) else None
    if not summary:
        summary = f"Spend in the last 24 hours was ${d['total_last_24h']:.2f} across {len(d['rows'])} segments; {len(d['anomalies'])} exceeded the {d['threshold_pct']:.0f}% threshold."
    if not isinstance(actions, list) or not actions:
        actions = ["Ask the owners of the flagged segments what changed", "Tighten the department budget if the spend is not planned", "Enable Smart routing for the feature that grew fastest"]
    output = {"summary_md": summary, "actions": [str(a) for a in actions][:3], "anomalies": d["anomalies"], "segments": top, "total_last_24h_usd": d["total_last_24h"]}
    return {"output": output, **step(state, "explain", f"Explained {len(d['anomalies'])} anomalies", kind="llm")}


def build(checkpointer):
    g = StateGraph(RunState)
    g.add_node("measure", measure)
    g.add_node("explain", explain)
    g.add_edge(START, "measure")
    g.add_edge("measure", "explain")
    g.add_edge("explain", END)
    return g.compile(checkpointer=checkpointer)


register(Blueprint(
    id="cost-sentinel", name="Cost sentinel", family="Platform", pattern="Measure against a baseline, alert, explain",
    summary="Compares the last 24 hours of spend per department and feature with the trailing week and raises an alert when a segment jumps.",
    description="A platform agent for admins and finance: computes spend per department and feature for the last day against a 7-day daily baseline, flags segments above a percentage threshold and a dollar floor, raises a 'cost' alert, and explains the anomalies with three concrete checks.",
    tiers={"measure": "deterministic", "explain": "Economy"},
    graph={"nodes": [{"id": "measure", "label": "Measure against baseline", "kind": "tool"}, {"id": "explain", "label": "Explain anomalies", "kind": "llm"}], "edges": [["measure", "explain"]], "columns": [["measure"], ["explain"]]},
    samples=[{"name": "Default thresholds", "input": {"threshold_pct": 50, "floor_usd": 0.5}}, {"name": "Strict", "input": {"threshold_pct": 25, "floor_usd": 0.1}}],
    datasets=[], flavors=["LangGraph"], review_gates=[], dashboard=["Anomalies", "Spend last 24h"], links={"origin": "/operate/cost"},
    build=build, input_schema={"threshold_pct": "number, default 50", "floor_usd": "number, default 0.5"}, batch=14,
))
