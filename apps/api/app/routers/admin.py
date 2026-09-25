from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_user
from app.catalog import catalog_payload
from app.config import settings
from app.db import get_db
from app.governance import DEFAULT_POLICIES, caps, policy_for, seed_defaults
from app.models import Alert, Budget, User

router = APIRouter(prefix="/v1/admin", tags=["admin"])
alerts_router = APIRouter(prefix="/v1/alerts", tags=["alerts"])

ROLES = ("admin", "champion", "builder", "explorer")


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


class UserPatch(BaseModel):
    role: str | None = Field(default=None, pattern="^(admin|champion|builder|explorer)$")
    department: str | None = None


class PolicyBody(BaseModel):
    allowed_tiers: list[str]
    allowed_providers: list[str] = Field(default_factory=list)
    max_tokens: int = Field(ge=256, le=128_000)
    smart_enabled: bool = True


class BudgetsBody(BaseModel):
    org_cap_usd: float = Field(ge=0)
    default_user_cap_usd: float = Field(ge=0)
    user_caps: dict[str, float] = Field(default_factory=dict)
    department_caps: dict[str, float] = Field(default_factory=dict)


@router.get("/users")
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    users = db.scalars(select(User).order_by(User.name)).all()
    return {"users": [{"id": u.id, "name": u.name, "email": u.email, "role": u.role, "department": u.department, "created_at": u.created_at.isoformat()} for u in users]}


@router.patch("/users/{user_id}")
def patch_user(user_id: str, body: UserPatch, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if body.role:
        user.role = body.role
    if body.department is not None:
        user.department = body.department
    db.commit()
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role, "department": user.department}


@router.get("/policies")
def get_policies(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    seed_defaults(db)
    out = []
    for role in ROLES:
        p = policy_for(db, role)
        out.append({"role": role, "allowed_tiers": p.allowed_tiers, "allowed_providers": p.allowed_providers, "max_tokens": p.max_tokens, "smart_enabled": p.smart_enabled})
    return {"policies": out, "tiers": ["Economy", "Workhorse", "Premium", "Frontier"], "providers": sorted({m["provider"] for m in catalog_payload()})}


@router.put("/policies/{role}")
def put_policy(role: str, body: PolicyBody, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    if role not in ROLES:
        raise HTTPException(status_code=404, detail="Unknown role")
    p = policy_for(db, role)
    p.allowed_tiers = body.allowed_tiers
    p.allowed_providers = body.allowed_providers
    p.max_tokens = body.max_tokens
    p.smart_enabled = body.smart_enabled
    db.commit()
    return {"role": role, "allowed_tiers": p.allowed_tiers, "allowed_providers": p.allowed_providers, "max_tokens": p.max_tokens, "smart_enabled": p.smart_enabled}


@router.post("/policies/reset")
def reset_policies(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    for role, cfg in DEFAULT_POLICIES.items():
        p = policy_for(db, role)
        for k, v in cfg.items():
            setattr(p, k, v)
    db.commit()
    return {"ok": True}


@router.get("/budgets")
def get_budgets(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    seed_defaults(db)
    rows = db.scalars(select(Budget)).all()
    users = {u.id: u for u in db.scalars(select(User))}
    return {
        "org_cap_usd": next((b.monthly_cap_usd for b in rows if b.scope == "org"), settings.org_monthly_cap_usd),
        "default_user_cap_usd": next((b.monthly_cap_usd for b in rows if b.scope == "user_default"), settings.default_user_cap_usd),
        "user_caps": [{"user_id": b.key, "name": users[b.key].name if b.key in users else b.key, "cap_usd": b.monthly_cap_usd} for b in rows if b.scope == "user"],
        "department_caps": [{"department": b.key, "cap_usd": b.monthly_cap_usd} for b in rows if b.scope == "department"],
        "departments": sorted({u.department for u in users.values()}),
    }


@router.put("/budgets")
def put_budgets(body: BudgetsBody, _: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    def upsert(scope: str, key: str, cap: float) -> None:
        row = db.scalar(select(Budget).where(Budget.scope == scope, Budget.key == key))
        if row is None:
            db.add(Budget(scope=scope, key=key, monthly_cap_usd=cap))
        else:
            row.monthly_cap_usd = cap

    upsert("org", "org", body.org_cap_usd)
    upsert("user_default", "user_default", body.default_user_cap_usd)
    for row in db.scalars(select(Budget).where(Budget.scope.in_(["user", "department"]))).all():
        db.delete(row)
    db.flush()
    for uid, cap in body.user_caps.items():
        db.add(Budget(scope="user", key=uid, monthly_cap_usd=cap))
    for dept, cap in body.department_caps.items():
        db.add(Budget(scope="department", key=dept, monthly_cap_usd=cap))
    db.commit()
    return {"ok": True}


@router.get("/settings")
def get_settings(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    models = catalog_payload()
    providers: dict[str, dict] = {}
    for m in models:
        p = providers.setdefault(m["provider"], {"provider": m["provider"], "env_key": m["env_key"], "configured": False, "models": 0, "docs_url": m["docs_url"]})
        p["models"] += 1
        p["configured"] = p["configured"] or m["available"]
    return {
        "environment": settings.environment,
        "fake_llm": settings.fake_llm,
        "database": settings.database_url.split("://")[0],
        "providers": sorted(providers.values(), key=lambda p: p["provider"]),
        "org_credits_usd": settings.org_credits_usd,
    }


@alerts_router.get("")
def list_alerts(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    stmt = select(Alert).order_by(Alert.created_at.desc()).limit(50)
    if user.role not in ("admin", "champion"):
        stmt = stmt.where(Alert.scope == "user", Alert.key == user.id)
    rows = db.scalars(stmt).all()
    return {
        "alerts": [
            {"id": a.id, "scope": a.scope, "key": a.key, "label": a.label, "threshold": a.threshold, "period": a.period,
             "spend_usd": a.spend_usd, "cap_usd": a.cap_usd, "acknowledged": a.acknowledged, "created_at": a.created_at.isoformat()}
            for a in rows
        ],
        "unread": sum(1 for a in rows if not a.acknowledged),
    }


@alerts_router.post("/{alert_id}/ack")
def ack_alert(alert_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    a = db.get(Alert, alert_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    a.acknowledged = True
    db.commit()
    return {"ok": True, "at": datetime.now(UTC).isoformat()}


@router.get("/budgets/me")
def my_caps(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return caps(db, user)
