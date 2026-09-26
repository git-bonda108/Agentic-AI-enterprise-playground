from __future__ import annotations

import threading

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.core import REGISTRY
from app.auth import current_user
from app.catalog_store import get_entry
from app.db import get_db
from app.evals import (
    CHECK_TYPES,
    DEFAULT_GATE,
    DEFAULT_RUBRIC,
    LEVELS,
    RUBRIC_LIBRARY,
    case_from_run,
    current_agent_version,
    execute_eval,
    hardening_for,
    next_due,
    run_canary,
    run_payload,
    schedule_payload,
    suite_payload,
    tick,
)
from app.governance import check_budget
from app.models import CanarySchedule, EvalRun, EvalSuite, Promotion, Run, User

router = APIRouter(prefix="/v1/evals", tags=["evals"])


class CaseBody(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    name: str = Field(default="", max_length=120)
    input: dict = Field(default_factory=dict)
    resume: object | None = None
    expect: dict = Field(default_factory=dict)


class SuiteBody(BaseModel):
    blueprint_id: str
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=600)
    cases: list[CaseBody] = Field(default_factory=list)
    rubric: dict = Field(default_factory=lambda: dict(DEFAULT_RUBRIC))
    gate: dict = Field(default_factory=lambda: dict(DEFAULT_GATE))


class SuitePatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=600)
    cases: list[CaseBody] | None = None
    rubric: dict | None = None
    gate: dict | None = None


class FromRunBody(BaseModel):
    run_id: str
    name: str | None = None


class CanaryBody(BaseModel):
    enabled: bool = True
    hour_utc: int = Field(default=2, ge=0, le=23)
    auto_rollback: bool = True
    max_pass_rate_drop: float = Field(default=10.0, ge=0, le=100)
    max_cost_increase_pct: float = Field(default=50.0, ge=0)
    max_latency_increase_pct: float = Field(default=100.0, ge=0)


class PromoteBody(BaseModel):
    level: int = Field(ge=0, le=4)
    note: str = Field(default="", max_length=400)


def _runnable(blueprint_id: str) -> bool:
    if blueprint_id in REGISTRY and REGISTRY[blueprint_id].family != "Runtime":
        return True
    entry = get_entry(blueprint_id)
    return bool(entry and entry.get("runnable"))


def _suite(suite_id: str, db: Session) -> EvalSuite:
    s = db.get(EvalSuite, suite_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Suite not found")
    return s


def _can_edit(s: EvalSuite, user: User) -> bool:
    return user.role == "admin" or (s.owner_id == user.id and not s.system)


@router.get("/library")
def library(_: User = Depends(current_user)) -> dict:
    return {"rubric": RUBRIC_LIBRARY, "checks": CHECK_TYPES, "levels": LEVELS, "default_gate": DEFAULT_GATE, "default_rubric": DEFAULT_RUBRIC}


@router.get("/suites")
def list_suites(blueprint_id: str = Query(default=""), _: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    stmt = select(EvalSuite).order_by(EvalSuite.system.desc(), EvalSuite.updated_at.desc())
    if blueprint_id:
        stmt = stmt.where(EvalSuite.blueprint_id == blueprint_id)
    return {"suites": [suite_payload(s, db) for s in db.scalars(stmt).all()]}


@router.post("/suites", status_code=201)
def create_suite(body: SuiteBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    if not _runnable(body.blueprint_id):
        raise HTTPException(status_code=404, detail="Unknown or non-runnable agent")
    s = EvalSuite(owner_id=user.id, blueprint_id=body.blueprint_id, name=body.name, description=body.description, cases=[c.model_dump(exclude_none=True) for c in body.cases], rubric=body.rubric, gate=body.gate)
    db.add(s)
    db.commit()
    return suite_payload(s, db)


@router.get("/suites/{suite_id}")
def get_suite(suite_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    s = _suite(suite_id, db)
    return {**suite_payload(s, db), "can_edit": _can_edit(s, user), "hardening": hardening_for(db, s.blueprint_id)}


@router.patch("/suites/{suite_id}")
def patch_suite(suite_id: str, body: SuitePatch, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    s = _suite(suite_id, db)
    if not _can_edit(s, user):
        raise HTTPException(status_code=403, detail="Only the owner or an admin can change this suite")
    data = body.model_dump(exclude_none=True)
    if "cases" in data:
        data["cases"] = [c.model_dump(exclude_none=True) for c in body.cases or []]
    for k, v in data.items():
        setattr(s, k, v)
    db.commit()
    return suite_payload(s, db)


@router.delete("/suites/{suite_id}", status_code=204)
def delete_suite(suite_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    s = _suite(suite_id, db)
    if s.system or not _can_edit(s, user):
        raise HTTPException(status_code=403, detail="System suites cannot be deleted")
    for r in db.scalars(select(EvalRun).where(EvalRun.suite_id == s.id)).all():
        db.delete(r)
    sched = db.scalar(select(CanarySchedule).where(CanarySchedule.suite_id == s.id))
    if sched:
        db.delete(sched)
    db.delete(s)
    db.commit()


@router.post("/suites/{suite_id}/cases/from-run", status_code=201)
def add_case_from_run(suite_id: str, body: FromRunBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    s = _suite(suite_id, db)
    if not _can_edit(s, user):
        raise HTTPException(status_code=403, detail="Only the owner or an admin can change this suite")
    run = db.get(Run, body.run_id)
    if run is None or run.blueprint_id != s.blueprint_id:
        raise HTTPException(status_code=404, detail="Run not found for this agent")
    case = case_from_run(run, body.name)
    s.cases = [*(s.cases or []), case]
    db.commit()
    return {"case": case, "suite": suite_payload(s, db)}


@router.post("/suites/{suite_id}/run", status_code=201)
def run_suite(suite_id: str, wait: bool = Query(default=False), user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    s = _suite(suite_id, db)
    if not s.cases:
        raise HTTPException(status_code=400, detail="Add at least one case first")
    budget = check_budget(db, user)
    if not budget.allowed:
        raise HTTPException(status_code=402, detail=budget.reason)
    er = EvalRun(suite_id=s.id, blueprint_id=s.blueprint_id, user_id=user.id, kind="manual", status="queued", agent_version=current_agent_version(db, s.blueprint_id))
    db.add(er)
    db.commit()
    if wait:
        execute_eval(er.id)
    else:
        threading.Thread(target=execute_eval, args=(er.id,), daemon=True).start()
    db.expire_all()
    return run_payload(db.get(EvalRun, er.id))


@router.get("/runs")
def list_runs(suite_id: str = Query(default=""), blueprint_id: str = Query(default=""), kind: str = Query(default=""), limit: int = Query(default=30, le=200), _: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    stmt = select(EvalRun).order_by(EvalRun.created_at.desc()).limit(limit)
    if suite_id:
        stmt = stmt.where(EvalRun.suite_id == suite_id)
    if blueprint_id:
        stmt = stmt.where(EvalRun.blueprint_id == blueprint_id)
    if kind:
        stmt = stmt.where(EvalRun.kind == kind)
    return {"runs": [run_payload(r, brief=True) for r in db.scalars(stmt).all()]}


@router.get("/runs/{run_id}")
def get_run(run_id: str, _: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    r = db.get(EvalRun, run_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return run_payload(r)


@router.get("/suites/{suite_id}/canary")
def get_canary(suite_id: str, _: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    s = _suite(suite_id, db)
    c = db.scalar(select(CanarySchedule).where(CanarySchedule.suite_id == s.id))
    return {"canary": schedule_payload(c) if c else None}


@router.put("/suites/{suite_id}/canary")
def put_canary(suite_id: str, body: CanaryBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    s = _suite(suite_id, db)
    if not (_can_edit(s, user) or (s.system and user.role in ("admin", "champion", "builder"))):
        raise HTTPException(status_code=403, detail="Not allowed to schedule this suite")
    c = db.scalar(select(CanarySchedule).where(CanarySchedule.suite_id == s.id))
    if c is None:
        c = CanarySchedule(suite_id=s.id)
        db.add(c)
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    c.next_due_at = next_due(c.hour_utc)
    db.commit()
    return {"canary": schedule_payload(c)}


@router.post("/suites/{suite_id}/canary/run", status_code=201)
def canary_now(suite_id: str, wait: bool = Query(default=False), user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    s = _suite(suite_id, db)
    c = db.scalar(select(CanarySchedule).where(CanarySchedule.suite_id == s.id))
    if c is None:
        raise HTTPException(status_code=400, detail="Enable the canary first")
    budget = check_budget(db, user)
    if not budget.allowed:
        raise HTTPException(status_code=402, detail=budget.reason)
    run_id = run_canary(c.id, wait=wait)
    db.expire_all()
    return run_payload(db.get(EvalRun, run_id))


@router.get("/canary")
def list_canaries(_: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(CanarySchedule).order_by(CanarySchedule.updated_at.desc())).all()
    out = []
    for c in rows:
        s = db.get(EvalSuite, c.suite_id)
        last = db.get(EvalRun, c.last_run_id) if c.last_run_id else None
        out.append({**schedule_payload(c), "suite": suite_payload(s) if s else None, "last_run": run_payload(last, brief=True) if last else None, "hardening": hardening_for(db, s.blueprint_id) if s else None})
    return {"canaries": out}


@router.post("/canary/tick")
def canary_tick(force: bool = Query(default=False), wait: bool = Query(default=False), user: User = Depends(current_user)) -> dict:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return {"started": tick(force=force, wait=wait)}


@router.get("/hardening")
def hardening(blueprint_id: str = Query(default=""), _: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    if blueprint_id:
        return hardening_for(db, blueprint_id)
    ids = sorted({s.blueprint_id for s in db.scalars(select(EvalSuite)).all()})
    return {"ladders": [hardening_for(db, i) for i in ids], "levels": LEVELS}


@router.post("/hardening/{blueprint_id}/promote")
def promote(blueprint_id: str, body: PromoteBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    ladder = hardening_for(db, blueprint_id)
    if body.level == 4 and ladder["achieved"] < 3:
        raise HTTPException(status_code=409, detail="Production needs level 3 evidence: a canary with three stable runs")
    db.add(Promotion(blueprint_id=blueprint_id, level=body.level, by_user=user.id, note=body.note))
    db.commit()
    return hardening_for(db, blueprint_id)
