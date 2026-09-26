"""Adoption analytics: hours per feature, outcomes, cost per outcome, time saved and an ROI matrix by department.

Hours are derived from the ledger. Events for one person are grouped into sessions (a gap of more than 30 minutes starts a new
one); a session lasts from its first to its last event plus a short tail, and its time is shared between the features used in
it in proportion to their events. Time saved multiplies outcomes by admin-editable minutes per outcome, shown as assumptions
next to every number so nobody mistakes an estimate for a measurement.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Assumption, Conversation, EvalRun, Message, Run, UsageEvent, User

SESSION_GAP = timedelta(minutes=30)
SESSION_TAIL = timedelta(minutes=4)

FEATURES = ["chat", "compare", "agent", "notebook", "knowledge", "eval"]
FEATURE_LABELS = {"chat": "Playground chat", "compare": "Model compare", "agent": "Agent runs", "notebook": "Notebooks", "knowledge": "Knowledge Spaces", "eval": "Evaluations"}

DEFAULT_ASSUMPTIONS: list[dict] = [
    {"key": "minutes_saved.chat", "value": 6.0, "label": "Minutes saved per answered conversation"},
    {"key": "minutes_saved.compare", "value": 10.0, "label": "Minutes saved per model comparison"},
    {"key": "minutes_saved.agent", "value": 25.0, "label": "Minutes saved per completed agent run"},
    {"key": "minutes_saved.notebook", "value": 15.0, "label": "Minutes saved per notebook execution"},
    {"key": "minutes_saved.knowledge", "value": 8.0, "label": "Minutes saved per document made searchable"},
    {"key": "minutes_saved.eval", "value": 30.0, "label": "Minutes saved per evaluation run"},
    {"key": "hourly_value_usd", "value": 60.0, "label": "Loaded hourly value of an employee (USD)"},
]


def ensure_assumptions(db: Session) -> None:
    existing = {a.key for a in db.scalars(select(Assumption)).all()}
    for a in DEFAULT_ASSUMPTIONS:
        if a["key"] not in existing:
            db.add(Assumption(**a))
    db.commit()


def assumptions(db: Session) -> dict[str, float]:
    return {a.key: a.value for a in db.scalars(select(Assumption)).all()}


def assumption_rows(db: Session) -> list[dict]:
    return [{"key": a.key, "value": a.value, "label": a.label, "updated_at": a.updated_at.isoformat()} for a in db.scalars(select(Assumption).order_by(Assumption.key)).all()]


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def session_hours(events: list[UsageEvent]) -> dict[str, dict[str, float]]:
    """Returns {user_id: {feature: hours}} from ledger events."""
    by_user: dict[str, list[UsageEvent]] = defaultdict(list)
    for e in events:
        by_user[e.user_id].append(e)
    out: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    def close(uid: str, session: list[UsageEvent]) -> None:
        if not session:
            return
        span = (_aware(session[-1].created_at) - _aware(session[0].created_at)) + SESSION_TAIL
        hours = span.total_seconds() / 3600
        counts: dict[str, int] = defaultdict(int)
        for e in session:
            counts[e.feature] += 1
        total = sum(counts.values())
        for feature, n in counts.items():
            out[uid][feature] += hours * n / total

    for uid, evs in by_user.items():
        evs.sort(key=lambda e: _aware(e.created_at))
        session: list[UsageEvent] = []
        for e in evs:
            if session and _aware(e.created_at) - _aware(session[-1].created_at) > SESSION_GAP:
                close(uid, session)
                session = []
            session.append(e)
        close(uid, session)
    return {u: dict(f) for u, f in out.items()}


def outcomes(db: Session, since: datetime) -> dict[str, dict[str, int]]:
    """Countable results per user per feature within the window."""
    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    answered = select(Message.conversation_id).where(Message.role == "assistant").distinct()
    for conv in db.scalars(select(Conversation).where(Conversation.created_at >= since, Conversation.id.in_(answered))).all():
        out[conv.user_id]["chat"] += 1
    for uid, _cid in db.execute(select(UsageEvent.user_id, UsageEvent.conversation_id).where(UsageEvent.feature == "compare", UsageEvent.created_at >= since).distinct()).all():
        out[uid]["compare"] += 1
    for run in db.scalars(select(Run).where(Run.status == "completed", Run.created_at >= since)).all():
        out[run.user_id]["agent"] += 1
    for (uid,) in db.execute(select(UsageEvent.user_id).where(UsageEvent.feature == "notebook", UsageEvent.created_at >= since)).all():
        out[uid]["notebook"] += 1
    for (uid,) in db.execute(select(UsageEvent.user_id).where(UsageEvent.feature == "knowledge", UsageEvent.created_at >= since)).all():
        out[uid]["knowledge"] += 1
    for er in db.scalars(select(EvalRun).where(EvalRun.status == "completed", EvalRun.created_at >= since)).all():
        out[er.user_id]["eval"] += 1
    return {u: dict(f) for u, f in out.items()}


def _blank() -> dict:
    return {"hours": 0.0, "outcomes": 0, "cost_usd": 0.0, "requests": 0, "users": set()}


def summary(db: Session, days: int = 30, department: str | None = None) -> dict:
    now = datetime.now(UTC)
    since = now - timedelta(days=days)
    users = {u.id: u for u in db.scalars(select(User)).all()}

    def in_scope(uid: str) -> bool:
        return not department or (uid in users and users[uid].department == department)

    events = [e for e in db.scalars(select(UsageEvent).where(UsageEvent.created_at >= since)).all() if in_scope(e.user_id)]
    hours = session_hours(events)
    outs = {u: f for u, f in outcomes(db, since).items() if in_scope(u)}
    asm = assumptions(db)
    hourly = asm.get("hourly_value_usd", 60.0)

    per_feature: dict[str, dict] = {f: {"feature": f, "label": FEATURE_LABELS[f], **_blank()} for f in FEATURES}

    def row(f: str) -> dict:
        return per_feature.setdefault(f, {"feature": f, "label": FEATURE_LABELS.get(f, f), **_blank()})

    for e in events:
        r = row(e.feature)
        r["cost_usd"] += e.cost_usd
        r["requests"] += 1
        r["users"].add(e.user_id)
    for feats in hours.values():
        for f, h in feats.items():
            row(f)["hours"] += h
    for feats in outs.values():
        for f, n in feats.items():
            row(f)["outcomes"] += n
    feature_rows = []
    for f, r in per_feature.items():
        minutes = asm.get(f"minutes_saved.{f}", 0.0)
        saved_h = r["outcomes"] * minutes / 60
        feature_rows.append({**r, "users": len(r["users"]), "hours": round(r["hours"], 2), "cost_usd": round(r["cost_usd"], 4), "cost_per_outcome_usd": round(r["cost_usd"] / r["outcomes"], 4) if r["outcomes"] else None, "minutes_saved_per_outcome": minutes, "hours_saved": round(saved_h, 2), "value_saved_usd": round(saved_h * hourly, 2)})
    feature_rows.sort(key=lambda r: -r["hours"])

    dept: dict[str, dict] = defaultdict(lambda: {"hours": 0.0, "outcomes": 0, "cost_usd": 0.0, "users": set(), "hours_saved": 0.0})

    def dept_of(uid: str) -> str:
        u = users.get(uid)
        return u.department if u else "Unknown"

    for e in events:
        d = dept[dept_of(e.user_id)]
        d["cost_usd"] += e.cost_usd
        d["users"].add(e.user_id)
    for uid, feats in hours.items():
        dept[dept_of(uid)]["hours"] += sum(feats.values())
    for uid, feats in outs.items():
        d = dept[dept_of(uid)]
        for f, n in feats.items():
            d["outcomes"] += n
            d["hours_saved"] += n * asm.get(f"minutes_saved.{f}", 0.0) / 60
    matrix = []
    for name, d in dept.items():
        value = d["hours_saved"] * hourly
        matrix.append({"department": name, "users": len(d["users"]), "hours": round(d["hours"], 2), "outcomes": d["outcomes"], "cost_usd": round(d["cost_usd"], 4), "hours_saved": round(d["hours_saved"], 2), "value_saved_usd": round(value, 2), "roi": round(value / d["cost_usd"], 1) if d["cost_usd"] > 0 else None})
    matrix.sort(key=lambda r: -r["hours_saved"])

    weeks: dict[str, dict] = {}
    for e in events:
        at = _aware(e.created_at)
        wk = (at - timedelta(days=at.weekday())).date().isoformat()
        w = weeks.setdefault(wk, {"week": wk, "requests": 0, "cost_usd": 0.0, "users": set()})
        w["requests"] += 1
        w["cost_usd"] += e.cost_usd
        w["users"].add(e.user_id)
    series = [{**w, "users": len(w["users"]), "cost_usd": round(w["cost_usd"], 4)} for w in sorted(weeks.values(), key=lambda w: w["week"])]

    total_hours = round(sum(r["hours"] for r in feature_rows), 2)
    total_outcomes = sum(r["outcomes"] for r in feature_rows)
    total_cost = round(sum(r["cost_usd"] for r in feature_rows), 4)
    total_saved = round(sum(r["hours_saved"] for r in feature_rows), 2)
    return {
        "days": days, "department": department, "since": since.isoformat(),
        "kpis": {"active_users": len({e.user_id for e in events}), "total_users": len(users), "hours": total_hours, "outcomes": total_outcomes, "cost_usd": total_cost, "cost_per_outcome_usd": round(total_cost / total_outcomes, 4) if total_outcomes else None, "hours_saved": total_saved, "value_saved_usd": round(total_saved * hourly, 2), "roi": round(total_saved * hourly / total_cost, 1) if total_cost > 0 else None},
        "features": feature_rows, "departments": matrix, "weekly": series, "assumptions": assumption_rows(db),
        "method": "Hours come from ledger sessions (30-minute gap, 4-minute tail, shared across features by event count). Time saved multiplies outcomes by the minutes in the assumptions. Value uses the loaded hourly rate. Estimates, not measurements.",
    }
