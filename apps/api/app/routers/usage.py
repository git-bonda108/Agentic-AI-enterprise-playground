import csv
import io
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adoption import session_hours
from app.agents.core import REGISTRY
from app.auth import current_user
from app.config import settings
from app.db import get_db
from app.models import Conversation, UsageEvent, User

HOUR_BUCKETS = {"chat": ("chat", "compare"), "agent": ("agent", "eval", "canary"), "notebook": ("notebook",), "sdk": ("sdk",)}

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
    by_key_source: dict[str, dict] = {}
    for e in events:
        ks = by_key_source.setdefault(e.key_source or "platform", {"key_source": e.key_source or "platform", "tokens": 0, "cost_usd": 0.0, "requests": 0})
        ks["tokens"] += e.tokens_in + e.tokens_out
        ks["cost_usd"] += e.cost_usd
        ks["requests"] += 1
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
        "hours": hours_for(db, user, days),
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
        "by_key_source": sorted(by_key_source.values(), key=lambda r: -r["cost_usd"]),
    }


def hours_for(db: Session, user: User, days: int) -> dict:
    """Hours per feature bucket for the window and the window before it, from ledger sessions (see app.adoption)."""
    now = datetime.now(UTC)
    since, before = now - timedelta(days=days), now - timedelta(days=2 * days)
    org_wide = user.role in ("admin", "champion")
    stmt = select(UsageEvent).where(UsageEvent.created_at >= before)
    if not org_wide:
        stmt = stmt.where(UsageEvent.user_id == user.id)
    events = db.scalars(stmt).all()
    current = [e for e in events if (e.created_at if e.created_at.tzinfo else e.created_at.replace(tzinfo=UTC)) >= since]
    previous = [e for e in events if e not in current]

    def bucketed(evs: list[UsageEvent]) -> dict[str, float]:
        per_feature: dict[str, float] = {}
        for feats in session_hours(evs).values():
            for f, h in feats.items():
                per_feature[f] = per_feature.get(f, 0.0) + h
        out = {b: round(sum(per_feature.get(f, 0.0) for f in feats), 2) for b, feats in HOUR_BUCKETS.items()}
        out["other"] = round(sum(h for f, h in per_feature.items() if not any(f in feats for feats in HOUR_BUCKETS.values())), 2)
        out["total"] = round(sum(per_feature.values()), 2)
        return out

    cur, prev = bucketed(current), bucketed(previous)
    people = {b: len({e.user_id for e in current if e.feature in feats}) for b, feats in HOUR_BUCKETS.items()}
    return {"window": cur, "previous": prev, "people": people, "days": days}


LAYERS = ("day", "department", "user", "feature", "model", "provider", "key_source", "conversation", "blueprint")
FILTERS = ("department", "user_id", "feature", "model", "provider", "key_source", "conversation_id", "blueprint_id", "day")


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _blueprint_names() -> dict[str, str]:
    return {bp_id: bp.name for bp_id, bp in REGISTRY.items()}


def _filtered_events(db: Session, user: User, days: int, filters: dict[str, str]) -> tuple[list[UsageEvent], dict[str, User], bool]:
    """Ledger rows in the window, scoped to the caller unless they lead the organisation, narrowed by the drill-down filters."""
    now = datetime.now(UTC)
    since = now - timedelta(days=days)
    org_wide = user.role in ("admin", "champion")
    stmt = select(UsageEvent).where(UsageEvent.created_at >= since)
    if not org_wide:
        stmt = stmt.where(UsageEvent.user_id == user.id)
    for col in ("user_id", "feature", "model", "provider", "key_source", "conversation_id", "blueprint_id"):
        if filters.get(col):
            stmt = stmt.where(getattr(UsageEvent, col) == filters[col])
    events = db.scalars(stmt.order_by(UsageEvent.created_at.desc())).all()
    users = {u.id: u for u in db.scalars(select(User))}
    if filters.get("department"):
        events = [e for e in events if (users.get(e.user_id).department if users.get(e.user_id) else "Unknown") == filters["department"]]
    if filters.get("day"):
        events = [e for e in events if _aware(e.created_at).date().isoformat() == filters["day"]]
    return events, users, org_wide


def _csv(rows: list[dict], filename: str) -> Response:
    buf = io.StringIO()
    names: list[str] = []
    for r in rows:
        for k in r:
            if k not in names:
                names.append(k)
    w = csv.DictWriter(buf, fieldnames=names, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/events", response_model=None)
def usage_events(
    days: int = Query(default=30, ge=1, le=365), limit: int = Query(default=50, ge=1, le=500), offset: int = Query(default=0, ge=0),
    department: str = "", user_id: str = "", feature: str = "", model: str = "", provider: str = "", key_source: str = "", conversation_id: str = "", blueprint_id: str = "", day: str = "",
    format: str = Query(default="json", pattern="^(json|csv)$"),
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> Response | dict:
    """The raw ledger rows behind any cost view: newest first, paged, the same filters as the breakdown, CSV on request."""
    filters = {k: v for k, v in {"department": department, "user_id": user_id, "feature": feature, "model": model, "provider": provider, "key_source": key_source, "conversation_id": conversation_id, "blueprint_id": blueprint_id, "day": day}.items() if v}
    events, users, org_wide = _filtered_events(db, user, days, filters)
    names = _blueprint_names()
    conv_ids = {e.conversation_id for e in events if e.conversation_id}
    titles = {c.id: c.title for c in db.scalars(select(Conversation).where(Conversation.id.in_(list(conv_ids))))} if conv_ids else {}

    def row(e: UsageEvent) -> dict:
        u = users.get(e.user_id)
        return {
            "id": e.id, "created_at": _aware(e.created_at).isoformat(timespec="seconds"), "user": u.name if u else e.user_id, "department": u.department if u else "",
            "feature": e.feature, "model": e.model, "provider": e.provider, "tokens_in": e.tokens_in, "tokens_out": e.tokens_out, "tokens_cached": e.tokens_cached,
            "cost_usd": round(e.cost_usd, 6), "latency_ms": e.latency_ms, "status": e.status, "key_source": e.key_source or "platform", "routed": bool(e.routed),
            "savings_usd": round(e.savings_usd or 0.0, 6), "conversation": titles.get(e.conversation_id or "", ""), "conversation_id": e.conversation_id,
            "run_id": e.run_id, "blueprint": names.get(e.blueprint_id or "", e.blueprint_id or ""), "blueprint_id": e.blueprint_id, "trace_id": e.trace_id,
        }

    if format == "csv":
        return _csv([row(e) for e in events], f"ledger-{days}d.csv")
    page = events[offset:offset + limit]
    return {"scope": "organization" if org_wide else "me", "days": days, "filters": filters, "total": len(events), "offset": offset, "limit": limit, "rows": [row(e) for e in page]}


@router.get("/breakdown", response_model=None)
def usage_breakdown(
    days: int = Query(default=30, ge=1, le=365), by: str = Query(default="model"),
    department: str = "", user_id: str = "", feature: str = "", model: str = "", provider: str = "", key_source: str = "", conversation_id: str = "", blueprint_id: str = "", day: str = "",
    format: str = Query(default="json", pattern="^(json|csv)$"),
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> Response | dict:
    """The cost cockpit: one layer at a time, always reconciled to the same ledger rows. Filters stack for the drill-down."""
    if by not in LAYERS:
        by = "model"
    filters = {k: v for k, v in {"department": department, "user_id": user_id, "feature": feature, "model": model, "provider": provider, "key_source": key_source, "conversation_id": conversation_id, "blueprint_id": blueprint_id, "day": day}.items() if v}
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    events, users, org_wide = _filtered_events(db, user, days, filters)
    bp_names = _blueprint_names()
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
        if by == "key_source":
            return (e.key_source or "platform"), ("Your key" if e.key_source == "personal" else "Platform key")
        if by == "conversation":
            cid = e.conversation_id or "-"
            return cid, conv_titles.get(cid, "Unsaved (compare or agent)")
        if by == "blueprint":
            bid = e.blueprint_id or "-"
            return bid, bp_names.get(bid, bid if e.blueprint_id else "Not a blueprint run")
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

    if format == "csv":
        return _csv([{"layer": by, **{k: v for k, v in r.items() if k != "latency_ms"}} for r in out], f"cost-by-{by}-{days}d.csv")
    total_cost = round(sum(e.cost_usd for e in events), 6)
    month_events = [e for e in events if _aware(e.created_at) >= month_start]
    spend_month = round(sum(e.cost_usd for e in month_events), 6)
    day_of_month = max(now.day, 1)
    days_in_month = 30
    return {
        "scope": "organization" if org_wide else "me",
        "by": by, "days": days, "filters": filters,
        "totals": {
            "cost_usd": total_cost,
            "tokens_in": sum(e.tokens_in for e in events),
            "tokens_out": sum(e.tokens_out for e in events),
            "tokens_cached": sum(e.tokens_cached for e in events),
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
