"""Policies (who may use what) and budgets (how much), enforced before every model call."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.catalog import CATALOG, ModelSpec
from app.config import settings
from app.models import Alert, Budget, Policy, UsageEvent, User

DEFAULT_POLICIES: dict[str, dict] = {
    "explorer": {"allowed_tiers": ["Economy", "Workhorse"], "allowed_providers": [], "max_tokens": 4096, "smart_enabled": True},
    "builder": {"allowed_tiers": ["Economy", "Workhorse", "Premium"], "allowed_providers": [], "max_tokens": 16384, "smart_enabled": True},
    "champion": {"allowed_tiers": ["Economy", "Workhorse", "Premium", "Frontier"], "allowed_providers": [], "max_tokens": 65536, "smart_enabled": True},
    "admin": {"allowed_tiers": ["Economy", "Workhorse", "Premium", "Frontier"], "allowed_providers": [], "max_tokens": 65536, "smart_enabled": True},
}
THRESHOLDS = (50, 80, 100)


def seed_defaults(db: Session) -> None:
    for role, cfg in DEFAULT_POLICIES.items():
        if db.get(Policy, role) is None:
            db.add(Policy(role=role, **cfg))
    if not db.scalar(select(Budget).where(Budget.scope == "org")):
        db.add(Budget(scope="org", key="org", monthly_cap_usd=settings.org_monthly_cap_usd))
    if not db.scalar(select(Budget).where(Budget.scope == "user_default")):
        db.add(Budget(scope="user_default", key="user_default", monthly_cap_usd=settings.default_user_cap_usd))
    db.commit()


def policy_for(db: Session, role: str) -> Policy:
    policy = db.get(Policy, role)
    if policy is None:
        cfg = DEFAULT_POLICIES.get(role, DEFAULT_POLICIES["explorer"])
        policy = Policy(role=role, **cfg)
        db.add(policy)
        db.commit()
    return policy


def allowed_model_ids(db: Session, role: str) -> set[str]:
    policy = policy_for(db, role)
    return {
        m.id for m in CATALOG
        if m.tier in (policy.allowed_tiers or []) and (not policy.allowed_providers or m.provider in policy.allowed_providers)
    }


def check_policy(db: Session, user: User, spec: ModelSpec) -> str | None:
    """Return a denial reason, or None when allowed."""
    policy = policy_for(db, user.role)
    if spec.tier not in (policy.allowed_tiers or []):
        return f"Your role ({user.role}) may not use {spec.tier.lower()} models. Ask an admin to change the policy."
    if policy.allowed_providers and spec.provider not in policy.allowed_providers:
        return f"Your role ({user.role}) may not use {spec.provider} models."
    return None


def month_period(now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    return now.strftime("%Y-%m")


def _month_spend(db: Session, user_id: str | None = None, department: str | None = None) -> float:
    now = datetime.now(UTC)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    stmt = select(func.sum(UsageEvent.cost_usd)).where(UsageEvent.created_at >= start)
    if user_id:
        stmt = stmt.where(UsageEvent.user_id == user_id)
    if department:
        stmt = stmt.where(UsageEvent.user_id.in_(select(User.id).where(User.department == department)))
    return float(db.scalar(stmt) or 0.0)


def caps(db: Session, user: User) -> dict[str, float]:
    org = db.scalar(select(Budget).where(Budget.scope == "org"))
    user_cap = db.scalar(select(Budget).where(Budget.scope == "user", Budget.key == user.id))
    default_cap = db.scalar(select(Budget).where(Budget.scope == "user_default"))
    dept = db.scalar(select(Budget).where(Budget.scope == "department", Budget.key == user.department))
    return {
        "org": org.monthly_cap_usd if org else settings.org_monthly_cap_usd,
        "user": user_cap.monthly_cap_usd if user_cap else (default_cap.monthly_cap_usd if default_cap else settings.default_user_cap_usd),
        "department": dept.monthly_cap_usd if dept else 0.0,
    }


@dataclass
class BudgetCheck:
    allowed: bool
    reason: str | None = None
    warnings: list[str] = field(default_factory=list)
    user_spend: float = 0.0
    user_cap: float = 0.0
    org_spend: float = 0.0
    org_cap: float = 0.0


def _raise_alerts(db: Session, scope: str, key: str, label: str, spend: float, cap: float) -> list[str]:
    warnings: list[str] = []
    if cap <= 0:
        return warnings
    pct = spend / cap * 100
    period = month_period()
    for threshold in THRESHOLDS:
        if pct >= threshold:
            exists = db.scalar(select(Alert).where(Alert.scope == scope, Alert.key == key, Alert.threshold == threshold, Alert.period == period))
            if exists is None:
                db.add(Alert(scope=scope, key=key, label=label, threshold=threshold, period=period, spend_usd=round(spend, 4), cap_usd=cap))
                db.commit()
            if threshold < 100:
                warnings.append(f"{label} is at {pct:.0f}% of its ${cap:,.0f} monthly cap")
    return warnings


def check_budget(db: Session, user: User) -> BudgetCheck:
    limits = caps(db, user)
    user_spend = _month_spend(db, user_id=user.id)
    org_spend = _month_spend(db)
    result = BudgetCheck(allowed=True, user_spend=user_spend, user_cap=limits["user"], org_spend=org_spend, org_cap=limits["org"])
    result.warnings += _raise_alerts(db, "user", user.id, f"{user.name}'s budget", user_spend, limits["user"])
    result.warnings += _raise_alerts(db, "org", "org", "Organization budget", org_spend, limits["org"])
    if limits["department"] > 0:
        dept_spend = _month_spend(db, department=user.department)
        result.warnings += _raise_alerts(db, "department", user.department, f"{user.department} budget", dept_spend, limits["department"])
        if dept_spend >= limits["department"]:
            result.allowed = False
            result.reason = f"The {user.department} department has reached its ${limits['department']:,.2f} monthly cap."
    if limits["user"] > 0 and user_spend >= limits["user"]:
        result.allowed = False
        result.reason = f"You have reached your ${limits['user']:,.2f} monthly cap. Ask an admin to raise it."
    if limits["org"] > 0 and org_spend >= limits["org"]:
        result.allowed = False
        result.reason = f"The organization has reached its ${limits['org']:,.0f} monthly cap."
    return result
