"""Traces: every run, SDK session and chat as a timeline of steps and metered calls."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.core import REGISTRY
from app.auth import current_user
from app.catalog_store import get_entry
from app.db import get_db
from app.models import Conversation, Run, UsageEvent, User

router = APIRouter(prefix="/v1/traces", tags=["traces"])


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _blueprint_name(bid: str) -> str:
    bp = REGISTRY.get(bid)
    if bp is not None:
        return bp.name
    entry = get_entry(bid)
    return entry["name"] if entry else bid


def _sum(events: list[UsageEvent]) -> dict:
    lat = sorted(e.latency_ms for e in events if e.latency_ms)
    return {
        "calls": len(events), "tokens": sum(e.tokens_in + e.tokens_out for e in events), "cost_usd": round(sum(e.cost_usd for e in events), 6),
        "latency_p50_ms": lat[len(lat) // 2] if lat else 0, "errors": sum(1 for e in events if e.status != "ok"), "models": sorted({e.model for e in events}),
    }


@router.get("")
def list_traces(days: int = Query(default=7, ge=1, le=90), kind: str = Query(default=""), limit: int = Query(default=100, le=300), user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    since = datetime.now(UTC) - timedelta(days=days)
    org_wide = user.role in ("admin", "champion")
    items: list[dict] = []
    if kind in ("", "run"):
        stmt = select(Run).where(Run.created_at >= since).order_by(Run.created_at.desc()).limit(limit)
        if not org_wide:
            stmt = stmt.where(Run.user_id == user.id)
        for r in db.scalars(stmt).all():
            items.append({"kind": "run", "id": r.id, "title": _blueprint_name(r.blueprint_id), "status": r.status, "source": r.source or "manual", "started_at": _aware(r.created_at).isoformat(), "steps": len(r.steps or []), "tokens": r.tokens_in + r.tokens_out, "cost_usd": round(r.cost_usd, 6), "user_id": r.user_id})
    if kind in ("", "sdk"):
        stmt = select(UsageEvent).where(UsageEvent.feature == "sdk", UsageEvent.created_at >= since).order_by(UsageEvent.created_at.asc())
        if not org_wide:
            stmt = stmt.where(UsageEvent.user_id == user.id)
        groups: dict[str, list[UsageEvent]] = {}
        for e in db.scalars(stmt).all():
            groups.setdefault(e.trace_id or f"call-{e.id}", []).append(e)
        for tid, evs in groups.items():
            s = _sum(evs)
            items.append({"kind": "sdk", "id": tid, "title": "SDK session" if not tid.startswith("call-") else "SDK call", "status": "error" if s["errors"] else "completed", "source": "gateway", "started_at": _aware(evs[0].created_at).isoformat(), "steps": s["calls"], "tokens": s["tokens"], "cost_usd": s["cost_usd"], "user_id": evs[0].user_id, "models": s["models"]})
    if kind in ("", "chat"):
        stmt = select(Conversation).where(Conversation.created_at >= since).order_by(Conversation.created_at.desc()).limit(limit)
        if not org_wide:
            stmt = stmt.where(Conversation.user_id == user.id)
        for c in db.scalars(stmt).all():
            evs = db.scalars(select(UsageEvent).where(UsageEvent.conversation_id == c.id)).all()
            s = _sum(evs)
            items.append({"kind": "chat", "id": c.id, "title": c.title, "status": "completed", "source": "playground", "started_at": _aware(c.created_at).isoformat(), "steps": s["calls"], "tokens": s["tokens"], "cost_usd": s["cost_usd"], "user_id": c.user_id, "models": s["models"]})
    items.sort(key=lambda i: i["started_at"], reverse=True)
    return {"traces": items[:limit], "days": days, "scope": "organization" if org_wide else "me"}


def _event_row(e: UsageEvent) -> dict:
    return {"type": "call", "at": _aware(e.created_at).isoformat(), "feature": e.feature, "model": e.model, "provider": e.provider, "tokens_in": e.tokens_in, "tokens_out": e.tokens_out, "cost_usd": e.cost_usd, "latency_ms": e.latency_ms, "status": e.status, "key_source": e.key_source, "routed": e.routed}


@router.get("/{kind}/{trace_id:path}")
def trace_detail(kind: str, trace_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    org_wide = user.role in ("admin", "champion")
    if kind == "run":
        r = db.get(Run, trace_id)
        if r is None or (r.user_id != user.id and not org_wide):
            raise HTTPException(status_code=404, detail="Trace not found")
        calls = db.scalars(select(UsageEvent).where(UsageEvent.run_id == r.id).order_by(UsageEvent.created_at)).all()
        timeline = [{"type": "step", "at": s.get("at"), "node": s.get("node"), "kind": s.get("kind"), "summary": s.get("summary"), "detail": s.get("detail") or {}} for s in (r.steps or [])] + [_event_row(e) for e in calls]
        timeline.sort(key=lambda t: t.get("at") or "")
        return {"kind": "run", "id": r.id, "title": _blueprint_name(r.blueprint_id), "status": r.status, "input": r.input, "output": r.output, "review": r.review, "error": r.error, "summary": _sum(calls), "timeline": timeline, "started_at": _aware(r.created_at).isoformat(), "finished_at": _aware(r.finished_at).isoformat() if r.finished_at else None}
    if kind == "sdk":
        stmt = select(UsageEvent).where(UsageEvent.feature == "sdk")
        stmt = stmt.where(UsageEvent.id == trace_id[5:]) if trace_id.startswith("call-") else stmt.where(UsageEvent.trace_id == trace_id)
        if not org_wide:
            stmt = stmt.where(UsageEvent.user_id == user.id)
        calls = db.scalars(stmt.order_by(UsageEvent.created_at)).all()
        if not calls:
            raise HTTPException(status_code=404, detail="Trace not found")
        return {"kind": "sdk", "id": trace_id, "title": "SDK session", "status": "error" if any(c.status != "ok" for c in calls) else "completed", "summary": _sum(calls), "timeline": [_event_row(e) for e in calls], "started_at": _aware(calls[0].created_at).isoformat(), "finished_at": _aware(calls[-1].created_at).isoformat()}
    if kind == "chat":
        c = db.get(Conversation, trace_id)
        if c is None or (c.user_id != user.id and not org_wide):
            raise HTTPException(status_code=404, detail="Trace not found")
        calls = db.scalars(select(UsageEvent).where(UsageEvent.conversation_id == c.id).order_by(UsageEvent.created_at)).all()
        timeline = [{"type": "message", "at": _aware(m.created_at).isoformat(), "role": m.role, "text": (m.content or "")[:600], "model": m.model} for m in c.messages] + [_event_row(e) for e in calls]
        timeline.sort(key=lambda t: t.get("at") or "")
        return {"kind": "chat", "id": c.id, "title": c.title, "status": "completed", "summary": _sum(calls), "timeline": timeline, "started_at": _aware(c.created_at).isoformat(), "finished_at": None}
    raise HTTPException(status_code=404, detail="Unknown trace kind")
