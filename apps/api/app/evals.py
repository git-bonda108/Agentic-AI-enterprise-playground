"""Evaluation engine: golden sets, deterministic checks, model-graded rubrics, gates, nightly canaries with drift and rollback, hardening levels.

The same harness the test suite uses for the built-in blueprints becomes a product feature: every suite runs each case as a real,
metered run, checks the output deterministically, optionally asks an Economy-tier judge to score rubric criteria, and records the
result. Canaries rerun a suite on a schedule, compare against the last good run and can roll a wizard agent back to its last
good version. Hardening levels are computed from evidence, never asserted.
"""

from __future__ import annotations

import json
import logging
import statistics
import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.core import REGISTRY, parse_json
from app.agents.golden import GOLDEN
from app.agents.runtime import resume_run, start_run
from app.catalog import get_model
from app.catalog_store import get_entry
from app.config import settings
from app.db import SessionLocal
from app.llm import ProviderError, complete
from app.models import (
    AgentVersion,
    Alert,
    CanarySchedule,
    CustomAgent,
    EvalRun,
    EvalSuite,
    Promotion,
    Run,
    UsageEvent,
    User,
)
from app.router import first_available

logger = logging.getLogger("playground.evals")

RUBRIC_LIBRARY: list[dict] = [
    {"id": "correctness", "name": "Correctness", "description": "The answer is factually right for the input and the knowledge provided, with no invented details.", "why": "The single most common failure: confident, wrong output."},
    {"id": "groundedness", "name": "Groundedness", "description": "Every claim is supported by the retrieved knowledge or tool results, and citations point to real sources.", "why": "Stops hallucinated policy or numbers reaching a decision."},
    {"id": "completeness", "name": "Completeness", "description": "The answer covers every part of the request and does not skip required elements.", "why": "Catches partial answers that look finished."},
    {"id": "format", "name": "Format compliance", "description": "The output follows the requested structure: sections, fields, markdown, JSON where asked.", "why": "Downstream systems and readers depend on the shape."},
    {"id": "tone", "name": "Tone and safety", "description": "Professional, unbiased, no sensitive data leaked, no advice outside the agent's remit.", "why": "Protects the organisation when output reaches customers or regulators."},
    {"id": "conciseness", "name": "Conciseness", "description": "No padding, no repetition; the reader gets the point quickly.", "why": "Shorter answers cost less and get read."},
]

CHECK_TYPES: list[dict] = [
    {"id": "status", "label": "Run status equals", "example": "completed", "explain": "The run must finish in this state."},
    {"id": "contains", "label": "Answer contains text", "example": "220 USD", "explain": "Case-insensitive substring of the markdown answer."},
    {"id": "not_contains", "label": "Answer must not contain", "example": "I don't know", "explain": "Guards against refusals or leaked placeholders."},
    {"id": "output_has", "label": "Output has keys", "example": "summary_md, citations", "explain": "Structured fields the output must include."},
    {"id": "output_eq", "label": "Output field equals", "example": "company=Tesla", "explain": "Exact value of a top-level output field."},
    {"id": "cites", "label": "Has at least one citation", "example": "true", "explain": "For grounded answers: the citations list is not empty."},
    {"id": "max_cost_usd", "label": "Cost at most (USD)", "example": "0.05", "explain": "Budget per case."},
    {"id": "max_ms", "label": "Latency at most (ms)", "example": "20000", "explain": "Wall-clock time per case."},
    {"id": "review_required", "label": "Human review happened", "example": "true", "explain": "The run paused at a review gate (or must not have)."},
    {"id": "anomaly_codes", "label": "Anomaly codes present", "example": "missing_po", "explain": "Document reconciliation specific."},
]

LEVELS: list[dict] = [
    {"level": 0, "name": "Draft", "requirement": "Runs on mock data."},
    {"level": 1, "name": "Golden", "requirement": "A suite with at least five cases and one completed evaluation."},
    {"level": 2, "name": "Gated", "requirement": "A gate is configured and the latest evaluation clears it."},
    {"level": 3, "name": "Canaried", "requirement": "A canary is enabled and the last three canary runs passed without drift."},
    {"level": 4, "name": "Production", "requirement": "Promoted by an administrator with a rollback path."},
]

DEFAULT_GATE = {"min_pass_rate": 90.0, "max_cost_per_case_usd": 0.5, "max_p95_ms": 60000}
DEFAULT_RUBRIC = {"criteria": [{"id": "correctness", "weight": 1.0}], "pass_threshold": 3.0}

_running: set[str] = set()
_lock = threading.Lock()


# ---------------------------------------------------------------- suites ----------------------------------------------------------------

def _case_name(inp: dict) -> str:
    first = next(iter(inp.values()), "")
    text = first if isinstance(first, str) else json.dumps(first)
    return (text[:60] or "case").strip()


def ensure_system_suites(db: Session) -> int:
    """Every built-in blueprint gets its golden set as a system suite, once."""
    created = 0
    for blueprint_id, cases in GOLDEN.items():
        exists = db.scalar(select(EvalSuite).where(EvalSuite.blueprint_id == blueprint_id, EvalSuite.system.is_(True)))
        if exists is not None:
            continue
        bp = REGISTRY.get(blueprint_id)
        db.add(EvalSuite(
            owner_id=None, blueprint_id=blueprint_id, name=f"{bp.name if bp else blueprint_id} golden set", description="Ten cases shipped with the blueprint. Deterministic checks on structure and outcomes; correctness judged by an Economy model.",
            cases=[{"id": f"g{i + 1}", "name": _case_name(c["input"]), "input": c["input"], **({"resume": c["resume"]} if "resume" in c else {}), "expect": c["expect"]} for i, c in enumerate(cases)],
            rubric=DEFAULT_RUBRIC, gate=DEFAULT_GATE, system=True,
        ))
        created += 1
    db.commit()
    return created


def suite_payload(s: EvalSuite, db: Session | None = None) -> dict:
    last = None
    canary = None
    if db is not None:
        last_run = db.scalar(select(EvalRun).where(EvalRun.suite_id == s.id, EvalRun.status == "completed").order_by(EvalRun.created_at.desc()))
        last = run_payload(last_run, brief=True) if last_run else None
        sched = db.scalar(select(CanarySchedule).where(CanarySchedule.suite_id == s.id))
        canary = schedule_payload(sched) if sched else None
    bp = REGISTRY.get(s.blueprint_id)
    entry = get_entry(s.blueprint_id) if bp is None else None
    return {
        "id": s.id, "owner_id": s.owner_id, "blueprint_id": s.blueprint_id, "blueprint_name": bp.name if bp else (entry["name"] if entry else s.blueprint_id),
        "name": s.name, "description": s.description, "cases": s.cases or [], "rubric": s.rubric or DEFAULT_RUBRIC, "gate": s.gate or DEFAULT_GATE, "system": s.system,
        "case_count": len(s.cases or []), "last_run": last, "canary": canary, "created_at": s.created_at.isoformat(), "updated_at": s.updated_at.isoformat(),
    }


def run_payload(r: EvalRun, brief: bool = False) -> dict:
    out = {
        "id": r.id, "suite_id": r.suite_id, "blueprint_id": r.blueprint_id, "user_id": r.user_id, "kind": r.kind, "status": r.status, "summary": r.summary or {},
        "baseline_run_id": r.baseline_run_id, "drift": r.drift, "agent_version": r.agent_version, "error": r.error, "created_at": r.created_at.isoformat(), "finished_at": r.finished_at.isoformat() if r.finished_at else None,
    }
    if not brief:
        out["results"] = r.results or []
    return out


def schedule_payload(c: CanarySchedule) -> dict:
    return {"id": c.id, "suite_id": c.suite_id, "enabled": c.enabled, "hour_utc": c.hour_utc, "auto_rollback": c.auto_rollback, "max_pass_rate_drop": c.max_pass_rate_drop, "max_cost_increase_pct": c.max_cost_increase_pct, "max_latency_increase_pct": c.max_latency_increase_pct, "last_run_id": c.last_run_id, "next_due_at": c.next_due_at.isoformat() if c.next_due_at else None, "consecutive_passes": c.consecutive_passes}


def case_from_run(run: Run, name: str | None = None) -> dict:
    """Promote a real run into a golden case: what it produced becomes what we expect."""
    out = run.output or {}
    expect: dict[str, Any] = {"status": "completed" if run.status == "completed" else run.status, "output_has": sorted(k for k in out if not k.endswith("_md"))[:8]}
    if out.get("citations"):
        expect["cites"] = True
    if any(s.get("kind") == "human" for s in (run.steps or [])):
        expect["review_required"] = True
    return {"id": f"r{run.id[:8]}", "name": name or _case_name(run.input or {}), "input": run.input or {}, "expect": expect, "from_run_id": run.id}


# ---------------------------------------------------------------- checks ----------------------------------------------------------------

def check_case(run: dict, expect: dict) -> list[dict]:
    """Deterministic expectations, each reported as a named check so the UI can explain a failure."""
    out = run.get("output") or {}
    answer = str(out.get("answer_md") or out.get("summary_md") or out.get("path_md") or json.dumps(out))
    steps = run.get("steps") or []
    checks: list[dict] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail[:300]})

    if "status" in expect:
        add("status", run.get("status") == expect["status"], f"status={run.get('status')} expected {expect['status']}")
    if "review_required" in expect:
        seen = any(s.get("kind") == "human" or "Clarified" in str(s.get("summary", "")) for s in steps)
        add("review_required", seen == bool(expect["review_required"]), f"review seen={seen}")
    for code in expect.get("anomaly_codes", []):
        add(f"anomaly:{code}", code in {a.get("code") for a in out.get("anomalies", [])}, f"anomaly codes: {sorted({a.get('code') for a in out.get('anomalies', [])})}")
    if "escalated_min" in expect:
        add("escalated_min", len(out.get("escalated", [])) >= expect["escalated_min"], f"{len(out.get('escalated', []))} escalated")
    if "anomalies_max" in expect:
        add("anomalies_max", len(out.get("anomalies", [])) <= expect["anomalies_max"], f"{len(out.get('anomalies', []))} anomalies")
    if "sources_min" in expect:
        add("sources_min", len(out.get("sources", [])) >= expect["sources_min"], f"{len(out.get('sources', []))} sources")
    if "attempts_max" in expect:
        add("attempts_max", out.get("attempts", 0) <= expect["attempts_max"], f"{out.get('attempts', 0)} attempts")
    for k, v in (expect.get("output_eq") or {}).items():
        add(f"output_eq:{k}", out.get(k) == v, f"{k}={out.get(k)!r} expected {v!r}")
    for k in expect.get("output_has", []):
        add(f"output_has:{k}", k in out, f"keys: {sorted(out.keys())[:12]}")
    if "levels" in expect:
        add("levels", len(out.get("path", {})) == expect["levels"], f"{len(out.get('path', {}))} levels")
    if "reference_contains" in expect:
        urls = " ".join(r.get("url", "") for refs in out.get("references", {}).values() for r in refs)
        add("reference_contains", expect["reference_contains"] in urls, urls[:200])
    if "blockers_min" in expect:
        add("blockers_min", len(out.get("blockers", [])) >= expect["blockers_min"], f"{len(out.get('blockers', []))} blockers")
    if "table_rows" in expect:
        add("table_rows", len(out.get("table", [])) == expect["table_rows"], f"{len(out.get('table', []))} rows")
    if expect.get("chart"):
        add("chart", bool(out.get("chart") and out["chart"].get("data")), "chart present" if out.get("chart") else "no chart")
    if "top_retrieved" in expect:
        top = (out.get("retrieved") or [{}])[0].get("id")
        add("top_retrieved", top == expect["top_retrieved"], f"top={top}")
    for needle in ([expect["contains"]] if isinstance(expect.get("contains"), str) else expect.get("contains", [])):
        add(f"contains:{needle[:30]}", needle.lower() in answer.lower(), f"answer {len(answer)} chars")
    for needle in ([expect["not_contains"]] if isinstance(expect.get("not_contains"), str) else expect.get("not_contains", [])):
        add(f"not_contains:{needle[:30]}", needle.lower() not in answer.lower(), "present" if needle.lower() in answer.lower() else "absent")
    if expect.get("cites"):
        add("cites", bool(out.get("citations")), f"{len(out.get('citations') or [])} citations")
    if "max_cost_usd" in expect:
        add("max_cost_usd", float(run.get("cost_usd") or 0) <= float(expect["max_cost_usd"]), f"cost {run.get('cost_usd')}")
    if "max_ms" in expect:
        add("max_ms", int(run.get("_ms") or 0) <= int(expect["max_ms"] or 0), f"{run.get('_ms')} ms")
    if not checks:
        add("completed", run.get("status") == "completed", f"status={run.get('status')}")
    return checks


def _judge_model(user: User | None) -> str:
    from app.governance import allowed_model_ids
    from app.keys import available_providers

    allowed = None
    with SessionLocal() as db:
        if user is not None:
            allowed = allowed_model_ids(db, user.role)
        providers = set(available_providers(db, None, "eval"))
    for tier in ("Economy", "Workhorse", "Premium"):
        spec = first_available(tier, allowed, providers)
        if spec:
            return spec.id
    raise ProviderError("No model available to judge: the platform has no provider key configured")


def judge(criterion: dict, case: dict, run: dict, user: User | None, eval_run_id: str, blueprint_id: str) -> dict:
    """Model-graded score 1 to 5 with a one-line rationale, metered as feature 'eval'."""
    out = run.get("output") or {}
    answer = str(out.get("answer_md") or out.get("summary_md") or out.get("path_md") or json.dumps(out))[:6000]
    items = out.get("retrieved") or out.get("knowledge_items") or out.get("sources") or out.get("tool_calls") or []
    knowledge = "\n\n".join(f"[{i.get('id', i.get('title', '?'))}] {i.get('title', '')}: {i.get('body') or i.get('snippet') or i.get('result') or ''}" for i in items if isinstance(i, dict))[:5000] if items else ""
    system = ("You are a strict but fair evaluator. Score the response on one criterion from 1 (fails) to 5 (excellent). "
              "Judge against the input and the knowledge shown. When no knowledge is shown, judge on general correctness and do not penalise missing citations. "
              "Respond with JSON only: {\"score\": <1-5>, \"rationale\": \"<one sentence>\"}.")
    user_msg = f"Criterion: {criterion['name']}. {criterion['description']}\n\nInput:\n{json.dumps(case.get('input'))[:1500]}\n\nKnowledge available to the agent:\n{knowledge or '(none)'}\n\nResponse:\n{answer}"
    model_id = _judge_model(user)
    try:
        text, usage = complete(model_id, [{"role": "system", "content": system}, {"role": "user", "content": user_msg}], max_tokens=200, temperature=0.0)  # platform key from the environment
    except ProviderError as exc:
        return {"criterion": criterion["id"], "score": None, "rationale": f"Judge unavailable: {exc}"[:200], "model": model_id}
    spec = get_model(model_id)
    with SessionLocal() as db:
        db.add(UsageEvent(user_id=user.id if user else "system", feature="eval", model=model_id, provider=spec.provider if spec else "unknown", tokens_in=usage.tokens_in, tokens_out=usage.tokens_out, tokens_cached=usage.tokens_cached, cost_usd=usage.cost_usd, latency_ms=usage.latency_ms, status="ok", run_id=eval_run_id, blueprint_id=blueprint_id))
        db.commit()
    parsed = parse_json(text, {"score": 4 if len(answer) > 40 else 1, "rationale": "Deterministic fallback: no JSON from the judge."})
    try:
        score = max(1, min(5, round(float(parsed.get("score", 3)))))
    except (TypeError, ValueError):
        score = 3
    return {"criterion": criterion["id"], "score": score, "rationale": str(parsed.get("rationale", ""))[:300], "model": model_id, "cost_usd": usage.cost_usd}


# ---------------------------------------------------------------- execution ----------------------------------------------------------------

def _resume_answer(case: dict, review: dict | None) -> Any:
    if "resume" in case:
        return case["resume"]
    options = (review or {}).get("options") or []
    return options[0] if options else "approve"


def _run_case(db: Session, suite: EvalSuite, case: dict, user_id: str, source: str = "eval") -> tuple[dict, int]:
    from app.routers.runs import _payload

    started = time.perf_counter()
    run = Run(blueprint_id=suite.blueprint_id, user_id=user_id, input=case.get("input") or {}, status="queued", source=source)
    db.add(run)
    db.commit()
    start_run(run, background=False)
    db.expire(run)
    run = db.get(Run, run.id)
    hops = 0
    while run.status == "waiting_review" and hops < 3:
        resume_run(run, _resume_answer(case, run.review), background=False)
        db.expire(run)
        run = db.get(Run, run.id)
        hops += 1
    ms = int((time.perf_counter() - started) * 1000)
    payload = _payload(run)
    payload["_ms"] = ms
    return payload, ms


def execute_eval(eval_run_id: str) -> None:
    """Run every case, check, judge, summarise, gate, and compare with the baseline. Safe to call in a thread."""
    with _lock:
        if eval_run_id in _running:
            return
        _running.add(eval_run_id)
    try:
        with SessionLocal() as db:
            er = db.get(EvalRun, eval_run_id)
            suite = db.get(EvalSuite, er.suite_id)
            user = db.get(User, er.user_id)
            er.status = "running"
            db.commit()
            rubric = suite.rubric or DEFAULT_RUBRIC
            criteria = [c for c in RUBRIC_LIBRARY if c["id"] in {x["id"] for x in rubric.get("criteria", [])}]
            weights = {x["id"]: float(x.get("weight", 1.0)) for x in rubric.get("criteria", [])}
            threshold = float(rubric.get("pass_threshold", 3.0))
            results = []
            for case in suite.cases or []:
                try:
                    run, ms = _run_case(db, suite, case, er.user_id, source=er.kind if er.kind == "canary" else "eval")
                    checks = check_case(run, case.get("expect") or {})
                    scores = [judge(c, case, run, user, er.id, suite.blueprint_id) for c in criteria] if run.get("status") == "completed" else []
                    scored = [s for s in scores if s.get("score") is not None]
                    avg = round(sum(s["score"] * weights.get(s["criterion"], 1.0) for s in scored) / max(1e-9, sum(weights.get(s["criterion"], 1.0) for s in scored)), 2) if scored else None
                    passed = all(c["passed"] for c in checks) and (avg is None or avg >= threshold)
                    results.append({"case_id": case.get("id"), "name": case.get("name"), "run_id": run["id"], "status": run.get("status"), "passed": passed, "checks": checks, "scores": scores, "avg_score": avg, "cost_usd": run.get("cost_usd", 0.0), "ms": ms, "error": run.get("error")})
                except Exception as exc:
                    logger.exception("eval case failed")
                    results.append({"case_id": case.get("id"), "name": case.get("name"), "run_id": None, "status": "failed", "passed": False, "checks": [], "scores": [], "avg_score": None, "cost_usd": 0.0, "ms": 0, "error": str(exc)[:300]})
                er.results = list(results)  # a new list each time: SQLAlchemy only notices JSON changes on reassignment
                db.commit()
            summary = summarise(results, suite.gate or DEFAULT_GATE)
            er.summary = summary
            er.status = "completed"
            er.finished_at = datetime.now(UTC)
            baseline = db.scalar(select(EvalRun).where(EvalRun.suite_id == suite.id, EvalRun.id != er.id, EvalRun.status == "completed").order_by(EvalRun.created_at.desc()))
            sched = db.scalar(select(CanarySchedule).where(CanarySchedule.suite_id == suite.id))
            if baseline is not None:
                er.baseline_run_id = baseline.id
                er.drift = compute_drift(baseline.summary or {}, summary, sched)
            db.commit()
    except Exception as exc:
        logger.exception("eval run %s failed", eval_run_id)
        with SessionLocal() as db:
            er = db.get(EvalRun, eval_run_id)
            if er is not None:
                er.status, er.error, er.finished_at = "failed", str(exc)[:800], datetime.now(UTC)
                db.commit()
    finally:
        with _lock:
            _running.discard(eval_run_id)


def summarise(results: list[dict], gate: dict) -> dict:
    n = len(results)
    passed = sum(1 for r in results if r["passed"])
    costs = [float(r.get("cost_usd") or 0) for r in results]
    lat = sorted(int(r.get("ms") or 0) for r in results)
    p95 = lat[min(len(lat) - 1, round(0.95 * (len(lat) - 1)))] if lat else 0
    scores = [r["avg_score"] for r in results if r.get("avg_score") is not None]
    pass_rate = round(passed / n * 100, 1) if n else 0.0
    cost_per_case = round(sum(costs) / n, 6) if n else 0.0
    gate_checks = {
        "min_pass_rate": pass_rate >= float(gate.get("min_pass_rate", 0)),
        "max_cost_per_case_usd": cost_per_case <= float(gate.get("max_cost_per_case_usd", 1e9)),
        "max_p95_ms": p95 <= int(gate.get("max_p95_ms", 10**9)),
    }
    return {"cases": n, "passed": passed, "pass_rate": pass_rate, "avg_score": round(statistics.mean(scores), 2) if scores else None, "cost_usd": round(sum(costs), 6), "cost_per_case_usd": cost_per_case, "p95_ms": p95, "gate": gate_checks, "gate_passed": all(gate_checks.values())}


def compute_drift(baseline: dict, current: dict, sched: CanarySchedule | None) -> dict:
    drop = round(float(baseline.get("pass_rate", 0)) - float(current.get("pass_rate", 0)), 1)
    b_cost, c_cost = float(baseline.get("cost_per_case_usd") or 0), float(current.get("cost_per_case_usd") or 0)
    cost_pct = round((c_cost - b_cost) / b_cost * 100, 1) if b_cost > 0 else 0.0
    b_lat, c_lat = float(baseline.get("p95_ms") or 0), float(current.get("p95_ms") or 0)
    lat_pct = round((c_lat - b_lat) / b_lat * 100, 1) if b_lat > 0 else 0.0
    limits = {"pass": sched.max_pass_rate_drop if sched else 10.0, "cost": sched.max_cost_increase_pct if sched else 50.0, "latency": sched.max_latency_increase_pct if sched else 100.0}
    reasons = []
    if drop > limits["pass"]:
        reasons.append(f"pass rate fell {drop:.0f} points")
    # relative deltas are noise on tiny baselines: cost must move by at least a tenth of a cent per case, latency by at least a second
    if cost_pct > limits["cost"] and (c_cost - b_cost) >= 0.001:
        reasons.append(f"cost per case up {cost_pct:.0f}%")
    if lat_pct > limits["latency"] and (c_lat - b_lat) >= 1000:
        reasons.append(f"p95 latency up {lat_pct:.0f}%")
    return {"pass_rate_drop": drop, "cost_delta_pct": cost_pct, "latency_delta_pct": lat_pct, "verdict": "drift" if reasons else "stable", "reasons": reasons}


# ---------------------------------------------------------------- canary ----------------------------------------------------------------

def next_due(hour_utc: int, now: datetime | None = None) -> datetime:
    now = now or datetime.now(UTC)
    candidate = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    return candidate if candidate > now else candidate + timedelta(days=1)


def current_agent_version(db: Session, blueprint_id: str) -> int | None:
    if not blueprint_id.startswith("custom-"):
        return None
    return 1 + len(db.scalars(select(AgentVersion).where(AgentVersion.agent_id == blueprint_id)).all())


def snapshot_agent(a: CustomAgent) -> dict:
    return {"name": a.name, "description": a.description, "instructions": a.instructions, "knowledge": a.knowledge or [], "tools": a.tools or [], "skills": a.skills or [], "starters": a.starters or [], "published": a.published}


def rollback_agent(db: Session, agent: CustomAgent, to_version: int, note: str) -> bool:
    """Restore the snapshot of `to_version`; the state being replaced is saved as a new version first."""
    target = db.scalar(select(AgentVersion).where(AgentVersion.agent_id == agent.id, AgentVersion.version == to_version))
    if target is None:
        return False
    current = current_agent_version(db, agent.id) or 1
    db.add(AgentVersion(agent_id=agent.id, version=current, snapshot=snapshot_agent(agent), note=note))
    for k, v in target.snapshot.items():
        setattr(agent, k, v)
    db.commit()
    return True


def run_canary(schedule_id: str, *, wait: bool = False) -> str:
    """Create and execute a canary run, then react to drift: alert, roll back, demote."""
    with SessionLocal() as db:
        sched = db.get(CanarySchedule, schedule_id)
        suite = db.get(EvalSuite, sched.suite_id)
        owner = suite.owner_id or db.scalar(select(User.id).where(User.role == "admin").order_by(User.created_at)) or "system"
        er = EvalRun(suite_id=suite.id, blueprint_id=suite.blueprint_id, user_id=owner, kind="canary", status="queued", agent_version=current_agent_version(db, suite.blueprint_id))
        db.add(er)
        db.flush()  # the id is generated at flush time
        sched.last_run_id = er.id
        sched.next_due_at = next_due(sched.hour_utc)
        db.commit()
        run_id = er.id

    def work() -> None:
        execute_eval(run_id)
        _react_to_canary(run_id)

    if wait:
        work()
    else:
        threading.Thread(target=work, daemon=True).start()
    return run_id


def _react_to_canary(run_id: str) -> None:
    with SessionLocal() as db:
        er = db.get(EvalRun, run_id)
        suite = db.get(EvalSuite, er.suite_id)
        sched = db.scalar(select(CanarySchedule).where(CanarySchedule.suite_id == suite.id))
        if er.status != "completed" or sched is None:
            return
        # the baseline is the last completed run that cleared its gate without drift; otherwise the most recent completed run
        candidates = db.scalars(select(EvalRun).where(EvalRun.suite_id == suite.id, EvalRun.id != er.id, EvalRun.status == "completed").order_by(EvalRun.created_at.desc())).all()
        good = next((c for c in candidates if (c.summary or {}).get("gate_passed") and (not c.drift or c.drift.get("verdict") == "stable")), candidates[0] if candidates else None)
        if good is not None:
            er.baseline_run_id = good.id
            er.drift = compute_drift(good.summary or {}, er.summary or {}, sched)
        drifted = bool(er.drift and er.drift.get("verdict") == "drift") or not (er.summary or {}).get("gate_passed")
        actions: list[str] = []
        if drifted:
            sched.consecutive_passes = 0
            reasons = (er.drift or {}).get("reasons") or (["gate not cleared"] if not (er.summary or {}).get("gate_passed") else [])
            message = f"Canary for '{suite.name}': " + "; ".join(reasons)
            if sched.auto_rollback and suite.blueprint_id.startswith("custom-") and good is not None and good.agent_version and er.agent_version and good.agent_version < er.agent_version:
                agent = db.get(CustomAgent, suite.blueprint_id)
                if agent is not None and rollback_agent(db, agent, good.agent_version, f"Automatic rollback by canary run {er.id[:8]}"):
                    actions.append(f"rolled back to version {good.agent_version}")
            level = hardening_for(db, suite.blueprint_id)["level"]
            if level > 0:
                db.add(Promotion(blueprint_id=suite.blueprint_id, level=max(0, level - 1), by_user="canary", note=message[:400]))
                actions.append(f"demoted to level {max(0, level - 1)}")
            db.add(Alert(scope="canary", key=suite.id, label=f"Canary drift: {suite.name}", threshold=0, period=datetime.now(UTC).strftime("%Y-%m"), spend_usd=float((er.summary or {}).get("pass_rate", 0)), cap_usd=float((good.summary or {}).get("pass_rate", 0)) if good else 0.0, kind="canary", message=(message + (" · " + ", ".join(actions) if actions else ""))[:2000]))
        else:
            sched.consecutive_passes += 1
        er.drift = {**(er.drift or {"verdict": "stable", "reasons": [], "pass_rate_drop": 0, "cost_delta_pct": 0, "latency_delta_pct": 0}), "actions": actions}
        db.commit()


def due_schedules(db: Session, force: bool = False) -> list[CanarySchedule]:
    now = datetime.now(UTC)
    rows = db.scalars(select(CanarySchedule).where(CanarySchedule.enabled.is_(True))).all()
    return [c for c in rows if force or c.next_due_at is None or (c.next_due_at if c.next_due_at.tzinfo else c.next_due_at.replace(tzinfo=UTC)) <= now]


def tick(*, force: bool = False, wait: bool = False) -> list[str]:
    with SessionLocal() as db:
        ids = [c.id for c in due_schedules(db, force)]
    return [run_canary(i, wait=wait) for i in ids]


_scheduler: threading.Thread | None = None


def start_scheduler() -> None:
    global _scheduler
    if not settings.canary_scheduler or _scheduler is not None:
        return

    def loop() -> None:
        while True:
            time.sleep(60)
            try:
                tick()
            except Exception:
                logger.exception("canary tick failed")

    _scheduler = threading.Thread(target=loop, daemon=True, name="canary-scheduler")
    _scheduler.start()


# ---------------------------------------------------------------- hardening ----------------------------------------------------------------

def hardening_for(db: Session, blueprint_id: str) -> dict:
    suites = db.scalars(select(EvalSuite).where(EvalSuite.blueprint_id == blueprint_id)).all()
    suite_ids = [s.id for s in suites]
    runs = db.scalars(select(EvalRun).where(EvalRun.suite_id.in_(suite_ids), EvalRun.status == "completed").order_by(EvalRun.created_at.desc())).all() if suite_ids else []
    latest = runs[0] if runs else None
    scheds = db.scalars(select(CanarySchedule).where(CanarySchedule.suite_id.in_(suite_ids), CanarySchedule.enabled.is_(True))).all() if suite_ids else []
    canary_runs = [r for r in runs if r.kind == "canary"][:3]
    evidence = {
        "suites": len(suites), "cases": max((len(s.cases or []) for s in suites), default=0), "evaluations": len(runs),
        "latest_pass_rate": (latest.summary or {}).get("pass_rate") if latest else None, "latest_gate_passed": bool((latest.summary or {}).get("gate_passed")) if latest else False,
        "canary_enabled": bool(scheds), "consecutive_passes": max((c.consecutive_passes for c in scheds), default=0),
        "last_canaries_stable": len(canary_runs) >= 3 and all((r.drift or {}).get("verdict", "stable") == "stable" and (r.summary or {}).get("gate_passed") for r in canary_runs),
    }
    achieved = 0
    if evidence["cases"] >= 5 and evidence["evaluations"] >= 1:
        achieved = 1
    if achieved == 1 and evidence["latest_gate_passed"]:
        achieved = 2
    if achieved == 2 and evidence["canary_enabled"] and (evidence["consecutive_passes"] >= 3 or evidence["last_canaries_stable"]):
        achieved = 3
    promo = db.scalar(select(Promotion).where(Promotion.blueprint_id == blueprint_id).order_by(Promotion.created_at.desc()))
    level = achieved
    if promo is not None:
        if promo.by_user == "canary":
            # a demotion holds until two stable, gate-clearing canary runs have followed it; Production still needs an admin
            recovered = [r for r in runs if r.kind == "canary" and r.created_at > promo.created_at and (r.summary or {}).get("gate_passed") and (r.drift or {}).get("verdict", "stable") == "stable"]
            level = min(achieved, 3) if len(recovered) >= 2 else min(achieved, promo.level)
        elif promo.level == 4:
            level = 4 if achieved >= 3 else achieved
        else:
            level = min(achieved, promo.level) if promo.level < achieved else achieved
    return {"blueprint_id": blueprint_id, "level": level, "achieved": achieved, "name": LEVELS[level]["name"], "levels": LEVELS, "evidence": evidence, "last_promotion": {"level": promo.level, "by": promo.by_user, "note": promo.note, "at": promo.created_at.isoformat()} if promo else None}
