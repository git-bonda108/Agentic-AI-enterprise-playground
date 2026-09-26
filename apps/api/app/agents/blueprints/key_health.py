"""Key health check: a platform agent that proves every configured platform key still works and alerts when one does not."""

from __future__ import annotations

import time
from datetime import UTC, datetime

from langgraph.graph import END, START, StateGraph

from app.agents.core import Blueprint, RunState, register, step
from app.agents.runtime import ctx_from_config
from app.db import SessionLocal


def probe(state: RunState, config) -> dict:
    from app.catalog import CATALOG
    from app.keys import PROVIDERS, platform_key
    from app.llm import ProviderError, complete
    from app.models import Alert

    results = []
    for provider in PROVIDERS:
        if not platform_key(provider):
            continue
        spec = min((m for m in CATALOG if m.provider == provider), key=lambda m: m.input_per_m + m.output_per_m, default=None)
        if spec is None:
            continue
        started = time.perf_counter()
        try:
            text, usage = complete(spec.id, [{"role": "user", "content": "Reply with the single word OK."}], max_tokens=5, temperature=0.0, api_key=platform_key(provider))
            results.append({"provider": provider, "model": spec.id, "ok": True, "latency_ms": usage.latency_ms, "cost_usd": usage.cost_usd, "reply": text.strip()[:20], "error": ""})
        except ProviderError as exc:
            results.append({"provider": provider, "model": spec.id, "ok": False, "latency_ms": int((time.perf_counter() - started) * 1000), "cost_usd": 0.0, "reply": "", "error": str(exc)[:240]})
    failures = [r for r in results if not r["ok"]]
    if failures:
        with SessionLocal() as db:
            db.add(Alert(scope="keys", key="platform", label=f"{len(failures)} platform key(s) rejected", threshold=0, period=datetime.now(UTC).strftime("%Y-%m"), spend_usd=0.0, cap_usd=0.0, kind="keys", message="; ".join(f"{f['provider']}: {f['error'][:120]}" for f in failures)[:2000]))
            db.commit()
    return {"data": {"results": results, "failures": failures}, **step(state, "probe", f"Probed {len(results)} platform key(s); {len(failures)} rejected", {"providers": [r["provider"] for r in results]})}


def report(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    d = state["data"]
    facts = "\n".join(f"- {r['provider']} ({r['model']}): {'OK' if r['ok'] else 'FAILED'} in {r['latency_ms']} ms" + (f" · {r['error']}" if r["error"] else "") for r in d["results"]) or "- no platform keys are configured"
    text = ctx.llm("Economy", "You write a five-line operational note for an admin about provider key health. Use only the facts. For each failure, name the provider and the one action to take (rotate the key in the provider console, then update the platform secret).", f"Facts:\n{facts}", max_tokens=300)
    output = {"report_md": text, "results": d["results"], "failures": [f["provider"] for f in d["failures"]], "checked_at": datetime.now(UTC).isoformat()}
    return {"output": output, **step(state, "report", f"Wrote the key health note ({len(d['failures'])} failures)", kind="llm")}


def build(checkpointer):
    g = StateGraph(RunState)
    g.add_node("probe", probe)
    g.add_node("report", report)
    g.add_edge(START, "probe")
    g.add_edge("probe", "report")
    g.add_edge("report", END)
    return g.compile(checkpointer=checkpointer)


register(Blueprint(
    id="key-health-check", name="Key health check", family="Platform", pattern="Probe every platform key, alert on failure",
    summary="Sends one tiny completion through every configured platform key and raises an alert for any provider that rejects it.",
    description="A platform agent for admins: probes each provider that has a platform key with its cheapest model, records latency and cost, raises a 'keys' alert naming the rejected providers, and writes a short note with the action to take. Run it after rotating keys or on a schedule.",
    tiers={"probe": "deterministic", "report": "Economy"},
    graph={"nodes": [{"id": "probe", "label": "Probe platform keys", "kind": "tool"}, {"id": "report", "label": "Write the note", "kind": "llm"}], "edges": [["probe", "report"]], "columns": [["probe"], ["report"]]},
    samples=[{"name": "Check all platform keys", "input": {}}],
    datasets=[], flavors=["LangGraph"], review_gates=[], dashboard=["Providers probed", "Failures"], links={"origin": "/admin/settings"},
    build=build, input_schema={}, batch=14,
))
