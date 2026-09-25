from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import current_user
from app.config import settings
from app.db import get_db
from app.models import Conversation, UsageEvent, User

router = APIRouter(prefix="/v1/usage", tags=["usage"])


@router.get("/summary")
def usage_summary(days: int = Query(default=7, ge=1, le=90), user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Organization-level summary for the console. Admins and champions see everyone; others see themselves."""
    return summary_for(db, user, days)


def summary_for(db: Session, user: User, days: int) -> dict:
    """The summary as a plain function so the MCP server and notebooks can reuse it."""
    now = datetime.now(UTC)
    since = now - timedelta(days=days)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    org_wide = user.role in ("admin", "champion")

    base = select(UsageEvent)
    if not org_wide:
        base = base.where(UsageEvent.user_id == user.id)

    def scalar(stmt):
        return db.scalar(stmt) or 0

    scope = (lambda s: s) if org_wide else (lambda s: s.where(UsageEvent.user_id == user.id))

    spend_month = float(scalar(scope(select(func.sum(UsageEvent.cost_usd)).where(UsageEvent.created_at >= month_start))))
    spend_window = float(scalar(scope(select(func.sum(UsageEvent.cost_usd)).where(UsageEvent.created_at >= since))))
    tokens_window = int(scalar(scope(select(func.sum(UsageEvent.tokens_in + UsageEvent.tokens_out)).where(UsageEvent.created_at >= since))))
    tokens_in = int(scalar(scope(select(func.sum(UsageEvent.tokens_in)).where(UsageEvent.created_at >= since))))
    cached = int(scalar(scope(select(func.sum(UsageEvent.tokens_cached)).where(UsageEvent.created_at >= since))))
    requests = int(scalar(scope(select(func.count(UsageEvent.id)).where(UsageEvent.created_at >= since))))
    errors = int(scalar(scope(select(func.count(UsageEvent.id)).where(UsageEvent.created_at >= since, UsageEvent.status == "error"))))
    active_users = int(scalar(scope(select(func.count(func.distinct(UsageEvent.user_id))).where(UsageEvent.created_at >= since))))

    # Per-day series (SQLite and Postgres both accept date() on timestamps for this purpose).
    events = db.scalars(scope(select(UsageEvent).where(UsageEvent.created_at >= since))).all()
    by_day: dict[str, dict] = {}
    for i in range(days):
        d = (since + timedelta(days=i + 1)).date().isoformat()
        by_day[d] = {"day": d, "tokens": 0, "cost_usd": 0.0, "requests": 0}
    by_model: dict[str, dict] = {}
    by_feature: dict[str, dict] = {}
    by_user: dict[str, dict] = {}
    for e in events:
        d = e.created_at.date().isoformat() if e.created_at.tzinfo else e.created_at.replace(tzinfo=UTC).date().isoformat()
        row = by_day.setdefault(d, {"day": d, "tokens": 0, "cost_usd": 0.0, "requests": 0})
        row["tokens"] += e.tokens_in + e.tokens_out
        row["cost_usd"] += e.cost_usd
        row["requests"] += 1
        m = by_model.setdefault(e.model, {"model": e.model, "provider": e.provider, "tokens": 0, "cost_usd": 0.0, "requests": 0})
        m["tokens"] += e.tokens_in + e.tokens_out
        m["cost_usd"] += e.cost_usd
        m["requests"] += 1
        f = by_feature.setdefault(e.feature, {"feature": e.feature, "tokens": 0, "cost_usd": 0.0, "requests": 0})
        f["tokens"] += e.tokens_in + e.tokens_out
        f["cost_usd"] += e.cost_usd
        f["requests"] += 1
        u = by_user.setdefault(e.user_id, {"user_id": e.user_id, "tokens": 0, "cost_usd": 0.0, "requests": 0})
        u["tokens"] += e.tokens_in + e.tokens_out
        u["cost_usd"] += e.cost_usd
        u["requests"] += 1

    if org_wide and by_user:
        names = {u.id: u for u in db.scalars(select(User).where(User.id.in_(list(by_user.keys()))))}
        for uid, row in by_user.items():
            row["name"] = names[uid].name if uid in names else uid
            row["department"] = names[uid].department if uid in names else ""

    return {
        "scope": "organization" if org_wide else "me",
        "days": days,
        "credits_usd": settings.org_credits_usd,
        "monthly_cap_usd": settings.org_monthly_cap_usd,
        "spend_month_usd": round(spend_month, 6),
        "spend_window_usd": round(spend_window, 6),
        "tokens_window": tokens_window,
        "cache_reuse_ratio": round(cached / tokens_in, 4) if tokens_in else 0.0,
        "requests": requests,
        "errors": errors,
        "active_users": active_users,
        "by_day": sorted(by_day.values(), key=lambda r: r["day"]),
        "by_model": sorted(by_model.values(), key=lambda r: -r["cost_usd"]),
        "by_feature": sorted(by_feature.values(), key=lambda r: -r["cost_usd"]),
        "by_user": sorted(by_user.values(), key=lambda r: -r["cost_usd"])[:20],
    }


LAYERS = ("day", "department", "user", "feature", "model", "provider", "conversation")


@router.get("/breakdown")
def usage_breakdown(
    days: int = Query(default=30, ge=1, le=365), by: str = Query(default="model"),
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> dict:
    """The cost cockpit: one layer at a time, always reconciled to the same ledger rows."""
    if by not in LAYERS:
        by = "model"
    now = datetime.now(UTC)
    since = now - timedelta(days=days)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    org_wide = user.role in ("admin", "champion")
    stmt = select(UsageEvent).where(UsageEvent.created_at >= since)
    if not org_wide:
        stmt = stmt.where(UsageEvent.user_id == user.id)
    events = db.scalars(stmt).all()
    users = {u.id: u for u in db.scalars(select(User))}
    conv_titles: dict[str, str] = {}
    if by == "conversation":
        ids = {e.conversation_id for e in events if e.conversation_id}
        if ids:
            conv_titles = {c.id: c.title for c in db.scalars(select(Conversation).where(Conversation.id.in_(list(ids))))}

    def key_of(e: UsageEvent) -> tuple[str, str]:
        u = users.get(e.user_id)
        if by == "day":
            d = (e.created_at if e.created_at.tzinfo else e.created_at.replace(tzinfo=UTC)).date().isoformat()
            return d, d
        if by == "department":
            d = u.department if u else "Unknown"
            return d, d
        if by == "user":
            return e.user_id, u.name if u else e.user_id
        if by == "feature":
            return e.feature, e.feature
        if by == "provider":
            return e.provider, e.provider
        if by == "conversation":
            cid = e.conversation_id or "-"
            return cid, conv_titles.get(cid, "Unsaved (compare or agent)")
        return e.model, e.model

    rows: dict[str, dict] = {}
    for e in events:
        k, label = key_of(e)
        r = rows.setdefault(k, {"key": k, "label": label, "tokens_in": 0, "tokens_out": 0, "tokens_cached": 0, "cost_usd": 0.0, "requests": 0, "errors": 0, "savings_usd": 0.0, "latency_ms": 0})
        r["tokens_in"] += e.tokens_in
        r["tokens_out"] += e.tokens_out
        r["tokens_cached"] += e.tokens_cached
        r["cost_usd"] += e.cost_usd
        r["requests"] += 1
        r["errors"] += 1 if e.status != "ok" else 0
        r["savings_usd"] += e.savings_usd or 0.0
        r["latency_ms"] += e.latency_ms
    out = []
    for r in rows.values():
        r["avg_latency_ms"] = int(r["latency_ms"] / r["requests"]) if r["requests"] else 0
        r["cost_usd"] = round(r["cost_usd"], 6)
        r["savings_usd"] = round(r["savings_usd"], 6)
        out.append(r)
    out.sort(key=lambda r: (r["key"] if by == "day" else -r["cost_usd"]))

    total_cost = round(sum(e.cost_usd for e in events), 6)
    month_events = [e for e in events if (e.created_at if e.created_at.tzinfo else e.created_at.replace(tzinfo=UTC)) >= month_start]
    spend_month = round(sum(e.cost_usd for e in month_events), 6)
    day_of_month = max(now.day, 1)
    days_in_month = 30
    return {
        "scope": "organization" if org_wide else "me",
        "by": by, "days": days,
        "totals": {
            "cost_usd": total_cost,
            "spend_month_usd": spend_month,
            "forecast_month_usd": round(spend_month / day_of_month * days_in_month, 4),
            "savings_usd": round(sum(e.savings_usd or 0.0 for e in events), 6),
            "routed_requests": sum(1 for e in events if e.routed),
            "requests": len(events),
            "errors": sum(1 for e in events if e.status != "ok"),
            "tokens": sum(e.tokens_in + e.tokens_out for e in events),
        },
        "rows": out,
    }
