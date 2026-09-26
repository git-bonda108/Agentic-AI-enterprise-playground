from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.core import REGISTRY
from app.agents.runtime import resume_run, start_run
from app.auth import current_user
from app.catalog_store import get_entry
from app.db import get_db
from app.governance import check_budget
from app.models import Run, User

router = APIRouter(prefix="/v1/runs", tags=["runs"])


class RunCreate(BaseModel):
    blueprint_id: str
    input: dict = Field(default_factory=dict)
    wait: bool = False  # run inline (tests and scripts); the UI polls instead


class ResumeBody(BaseModel):
    answer: Any


def _payload(run: Run, users: dict[str, User] | None = None) -> dict:
    bp = REGISTRY.get(run.blueprint_id)
    entry = get_entry(run.blueprint_id) if bp is None else None
    user = users.get(run.user_id) if users else None
    return {
        "id": run.id, "blueprint_id": run.blueprint_id, "blueprint_name": bp.name if bp else entry["name"] if entry else run.blueprint_id, "user_id": run.user_id,
        "user_name": user.name if user else None, "status": run.status, "input": run.input, "output": run.output, "steps": run.steps or [],
        "source": run.source or "manual", "review": run.review, "error": run.error, "cost_usd": run.cost_usd, "tokens_in": run.tokens_in, "tokens_out": run.tokens_out,
        "created_at": run.created_at.isoformat(), "updated_at": run.updated_at.isoformat(), "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


def _owned(run_id: str, user: User, db: Session) -> Run:
    run = db.get(Run, run_id)
    if run is None or (run.user_id != user.id and user.role not in ("admin", "champion")):
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("", status_code=201)
def create_run(body: RunCreate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    entry = get_entry(body.blueprint_id)
    if body.blueprint_id not in REGISTRY and (entry is None or not entry.get("runnable")):
        raise HTTPException(status_code=404, detail="Unknown or non-runnable blueprint")
    if body.blueprint_id == "prompt-agent":
        raise HTTPException(status_code=404, detail="Pick a catalog entry to run")
    budget = check_budget(db, user)
    if not budget.allowed:
        raise HTTPException(status_code=402, detail=budget.reason)
    run = Run(blueprint_id=body.blueprint_id, user_id=user.id, input=body.input, status="queued")
    db.add(run)
    db.commit()
    start_run(run, background=not body.wait)
    db.refresh(run)
    if body.wait:
        db.expire(run)
        run = db.get(Run, run.id)
    return _payload(run)


@router.get("")
def list_runs(blueprint_id: str = Query(default=""), status: str = Query(default=""), limit: int = Query(default=50, le=200), user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    stmt = select(Run).order_by(Run.created_at.desc()).limit(limit)
    if user.role not in ("admin", "champion"):
        stmt = stmt.where(Run.user_id == user.id)
    if blueprint_id:
        stmt = stmt.where(Run.blueprint_id == blueprint_id)
    if status:
        stmt = stmt.where(Run.status == status)
    runs = db.scalars(stmt).all()
    users = {u.id: u for u in db.scalars(select(User))}
    return {"runs": [_payload(r, users) for r in runs], "waiting_review": sum(1 for r in runs if r.status == "waiting_review")}


@router.get("/{run_id}")
def get_run(run_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    run = _owned(run_id, user, db)
    users = {u.id: u for u in db.scalars(select(User).where(User.id == run.user_id))}
    return _payload(run, users)


@router.post("/{run_id}/resume")
def resume(run_id: str, body: ResumeBody, wait: bool = Query(default=False), user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    run = _owned(run_id, user, db)
    if run.status != "waiting_review":
        raise HTTPException(status_code=409, detail=f"Run is {run.status}, not waiting for review")
    resume_run(run, body.answer, background=not wait)
    db.expire(run)
    run = db.get(Run, run_id)
    return _payload(run)
