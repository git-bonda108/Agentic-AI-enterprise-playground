from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_db
from app.governance import allowed_model_ids, policy_for
from app.models import User
from app.router import route

router = APIRouter(prefix="/v1/route", tags=["routing"])


class RoutePreviewRequest(BaseModel):
    prompt: str


@router.post("/preview")
def preview(body: RoutePreviewRequest, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    policy = policy_for(db, user.role)
    if not policy.smart_enabled:
        return {"enabled": False, "reason": "Smart routing is disabled for your role."}
    decision = route(body.prompt, allowed_model_ids(db, user.role))
    if decision is None:
        return {"enabled": True, "decision": None, "reason": "No model is available for your role."}
    return {
        "enabled": True,
        "decision": {
            "tier": decision.tier, "model": decision.model, "reason": decision.reason, "baseline_model": decision.baseline_model,
            "est_cost_usd": decision.est_cost_usd, "est_baseline_cost_usd": decision.est_baseline_cost_usd,
            "est_savings_pct": decision.est_savings_pct,
        },
    }
