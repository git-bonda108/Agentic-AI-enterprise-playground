from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.adoption import assumption_rows, summary
from app.auth import current_user
from app.db import get_db
from app.governance import check_budget
from app.models import Assumption, Run, User
from app.routers.admin import require_admin

router = APIRouter(prefix="/v1/adoption", tags=["adoption"])


class AssumptionsBody(BaseModel):
    values: dict[str, float] = Field(default_factory=dict)


class DigestBody(BaseModel):
    days: int = Field(default=7, ge=1, le=365)
    department: str | None = None
    audience: str = Field(default="team leads", max_length=60)


@router.get("/summary")
def adoption_summary(days: int = Query(default=30, ge=1, le=365), department: str = Query(default=""), user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    if user.role not in ("admin", "champion"):
        department = user.department  # people see their own department; leaders see everything
    return summary(db, days=days, department=department or None)


@router.get("/assumptions")
def get_assumptions(_: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return {"assumptions": assumption_rows(db)}


@router.put("/assumptions")
def put_assumptions(body: AssumptionsBody, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    for key, value in body.values.items():
        row = db.get(Assumption, key)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Unknown assumption {key}")
        row.value = float(value)
    db.commit()
    return {"assumptions": assumption_rows(db)}


@router.post("/digest", status_code=201)
def digest(body: DigestBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Runs the adoption-digest platform agent synchronously and returns the run, metered like any other."""
    from app.agents.runtime import start_run
    from app.routers.runs import _payload

    budget = check_budget(db, user)
    if not budget.allowed:
        raise HTTPException(status_code=402, detail=budget.reason)
    run = Run(blueprint_id="adoption-digest", user_id=user.id, input={"days": body.days, "department": body.department, "audience": body.audience}, status="queued")
    db.add(run)
    db.commit()
    start_run(run, background=False)
    db.expire_all()
    return _payload(db.get(Run, run.id))
