"""Community: showcase, challenges judged by the evaluation engine, achievements from evidence, leaderboards from the ledger."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.evals import DEFAULT_GATE, execute_eval
from app.models import (
    Achievement,
    CanarySchedule,
    Challenge,
    ChallengeSubmission,
    Conversation,
    CustomAgent,
    EvalRun,
    EvalSuite,
    KnowledgeSpace,
    Run,
    ShowcaseComment,
    ShowcaseItem,
    ShowcaseLike,
    UsageEvent,
    User,
)

ACHIEVEMENTS: list[dict] = [
    {"key": "first_prompt", "name": "First prompt", "description": "Sent your first message in the playground.", "target": 1, "icon": "sparkles"},
    {"key": "comparer", "name": "Comparer", "description": "Compared models side by side.", "target": 1, "icon": "columns"},
    {"key": "smart_saver", "name": "Smart saver", "description": "Saved one dollar with Smart routing.", "target": 1, "icon": "piggy-bank"},
    {"key": "agent_runner", "name": "Agent runner", "description": "Completed ten agent runs.", "target": 10, "icon": "bot"},
    {"key": "reviewer", "name": "Reviewer", "description": "Resolved a human review gate.", "target": 1, "icon": "check-circle"},
    {"key": "builder", "name": "Builder", "description": "Created an agent in the wizard.", "target": 1, "icon": "hammer"},
    {"key": "librarian", "name": "Librarian", "description": "Filled a Knowledge Space with three documents.", "target": 3, "icon": "book-open"},
    {"key": "evaluator", "name": "Evaluator", "description": "Ran an evaluation suite.", "target": 1, "icon": "clipboard-check"},
    {"key": "canary_keeper", "name": "Canary keeper", "description": "Scheduled a nightly canary.", "target": 1, "icon": "radar"},
    {"key": "notebook", "name": "Notebook hand", "description": "Executed code in the sandbox.", "target": 1, "icon": "notebook-pen"},
    {"key": "publisher", "name": "Publisher", "description": "Published to the showcase.", "target": 1, "icon": "megaphone"},
    {"key": "champion", "name": "Champion", "description": "Won a challenge.", "target": 1, "icon": "trophy"},
]

POINTS = {"requests": 1, "outcomes": 5, "savings_usd": 20, "agents": 25, "suites": 20, "likes": 5, "achievements": 10, "challenge_wins": 100}


# ---------------------------------------------------------------- showcase ----------------------------------------------------------------

def showcase_payload(item: ShowcaseItem, db: Session, user: User | None = None, with_comments: bool = False) -> dict:
    owner = db.get(User, item.owner_id)
    out = {
        "id": item.id, "owner_id": item.owner_id, "owner_name": owner.name if owner else item.owner_id, "owner_department": owner.department if owner else "", "kind": item.kind, "ref_id": item.ref_id,
        "title": item.title, "summary": item.summary, "tags": item.tags or [], "outcome": item.outcome, "likes": item.likes, "views": item.views, "created_at": item.created_at.isoformat(),
        "link": {"agent": f"/build/agents?blueprint={item.ref_id}", "run": f"/operate/runs/{item.ref_id}", "conversation": f"/build/playground?conversation={item.ref_id}", "suite": f"/evaluate/evals?suite={item.ref_id}"}.get(item.kind, "/community/showcase"),
        "liked": bool(user and db.scalar(select(ShowcaseLike).where(ShowcaseLike.item_id == item.id, ShowcaseLike.user_id == user.id))),
    }
    if with_comments:
        rows = db.scalars(select(ShowcaseComment).where(ShowcaseComment.item_id == item.id).order_by(ShowcaseComment.created_at)).all()
        names = {u.id: u.name for u in db.scalars(select(User).where(User.id.in_({r.user_id for r in rows}))).all()} if rows else {}
        out["comments"] = [{"id": c.id, "user_id": c.user_id, "user_name": names.get(c.user_id, c.user_id), "body": c.body, "created_at": c.created_at.isoformat()} for c in rows]
    return out


def toggle_like(db: Session, item: ShowcaseItem, user: User) -> bool:
    existing = db.scalar(select(ShowcaseLike).where(ShowcaseLike.item_id == item.id, ShowcaseLike.user_id == user.id))
    if existing:
        db.delete(existing)
        item.likes = max(0, item.likes - 1)
        db.commit()
        return False
    db.add(ShowcaseLike(item_id=item.id, user_id=user.id))
    item.likes += 1
    db.commit()
    return True


# ---------------------------------------------------------------- challenges ----------------------------------------------------------------

def _agent_name(db: Session, agent_id: str) -> str:
    from app.agents.core import REGISTRY

    if agent_id in REGISTRY:
        return REGISTRY[agent_id].name
    a = db.get(CustomAgent, agent_id) if agent_id.startswith("custom-") else None
    return a.name if a else agent_id


def challenge_payload(c: Challenge, db: Session) -> dict:
    subs = db.scalars(select(ChallengeSubmission).where(ChallengeSubmission.challenge_id == c.id).order_by(ChallengeSubmission.created_at)).all()
    names = {u.id: u for u in db.scalars(select(User).where(User.id.in_({s.user_id for s in subs} | {c.owner_id}))).all()}
    standings = sorted([s for s in subs if s.score is not None], key=lambda s: -(s.score or 0))
    rank = {s.id: i + 1 for i, s in enumerate(standings)}
    owner = names.get(c.owner_id)
    now = datetime.now(UTC)
    ends = (c.ends_at if c.ends_at.tzinfo else c.ends_at.replace(tzinfo=UTC)) if c.ends_at else None
    return {
        "id": c.id, "owner_id": c.owner_id, "owner_name": owner.name if owner else c.owner_id, "title": c.title, "brief": c.brief, "cases": c.cases or [], "rubric": c.rubric or {}, "badge": c.badge,
        "status": c.status, "ends_at": ends.isoformat() if ends else None, "time_left_h": round((ends - now).total_seconds() / 3600, 1) if ends else None,
        "winner_submission_id": c.winner_submission_id, "created_at": c.created_at.isoformat(), "submission_count": len(subs),
        "submissions": [{
            "id": s.id, "user_id": s.user_id, "user_name": names[s.user_id].name if s.user_id in names else s.user_id, "department": names[s.user_id].department if s.user_id in names else "", "agent_id": s.agent_id, "agent_name": _agent_name(db, s.agent_id),
            "note": s.note, "score": s.score, "judged": s.judged, "eval_run_id": s.eval_run_id, "rank": rank.get(s.id), "created_at": s.created_at.isoformat(),
        } for s in subs],
    }


def judge_submission(db: Session, challenge: Challenge, sub: ChallengeSubmission) -> ChallengeSubmission:
    """Every submission is judged the same way: a suite built from the challenge's cases and rubric, run against the submitted agent."""
    suite = db.scalar(select(EvalSuite).where(EvalSuite.blueprint_id == sub.agent_id, EvalSuite.name == f"Challenge: {challenge.title}"))
    if suite is None:
        suite = EvalSuite(owner_id=challenge.owner_id, blueprint_id=sub.agent_id, name=f"Challenge: {challenge.title}", description=f"Judging suite for {challenge.title}", cases=[{"id": f"ch{i + 1}", "name": str(next(iter(c.get("input", {}).values()), "case"))[:60], "input": c.get("input", {}), "expect": c.get("expect") or {"status": "completed"}} for i, c in enumerate(challenge.cases or [])], rubric=challenge.rubric or {"criteria": [{"id": "correctness", "weight": 1}], "pass_threshold": 3.0}, gate=DEFAULT_GATE)
        db.add(suite)
        db.commit()
    er = EvalRun(suite_id=suite.id, blueprint_id=sub.agent_id, user_id=sub.user_id, kind="manual", status="queued")
    db.add(er)
    db.commit()
    execute_eval(er.id)
    db.expire_all()
    er = db.get(EvalRun, er.id)
    s = er.summary or {}
    # score out of 100: 60 percent rubric quality, 40 percent pass rate, so a fast wrong answer cannot win
    quality = (float(s.get("avg_score") or 0) / 5) * 60
    pass_part = float(s.get("pass_rate") or 0) * 0.4
    sub.eval_run_id = er.id
    sub.score = round(quality + pass_part, 1)
    sub.judged = {"avg_score": s.get("avg_score"), "pass_rate": s.get("pass_rate"), "cost_usd": s.get("cost_usd"), "p95_ms": s.get("p95_ms"), "cases": s.get("cases")}
    db.commit()
    return sub


def close_challenge(db: Session, challenge: Challenge) -> dict:
    subs = [s for s in db.scalars(select(ChallengeSubmission).where(ChallengeSubmission.challenge_id == challenge.id)).all() if s.score is not None]
    challenge.status = "closed"
    if subs:
        winner = max(subs, key=lambda s: (s.score or 0, -s.created_at.timestamp()))
        challenge.winner_submission_id = winner.id
        if db.scalar(select(Achievement).where(Achievement.user_id == winner.user_id, Achievement.key == "champion")) is None:
            db.add(Achievement(user_id=winner.user_id, key="champion"))
    db.commit()
    return challenge_payload(challenge, db)


# ---------------------------------------------------------------- achievements ----------------------------------------------------------------

def progress_for(db: Session, user: User) -> dict[str, int]:
    def count(stmt) -> int:
        return int(db.scalar(stmt) or 0)

    savings = float(db.scalar(select(func.sum(UsageEvent.savings_usd)).where(UsageEvent.user_id == user.id)) or 0.0)
    biggest_space = db.scalar(select(func.max(KnowledgeSpace.doc_count)).where(KnowledgeSpace.owner_id == user.id)) or 0
    reviewed = sum(1 for r in db.scalars(select(Run).where(Run.user_id == user.id, Run.status == "completed")).all() if any(s.get("kind") == "human" and ("Human decision" in str(s.get("summary", "")) or "Clarified" in str(s.get("summary", ""))) for s in (r.steps or [])))
    canaries = count(select(func.count(CanarySchedule.id)).join(EvalSuite, EvalSuite.id == CanarySchedule.suite_id).where(EvalSuite.owner_id == user.id, CanarySchedule.enabled.is_(True)))
    wins = count(select(func.count(Achievement.id)).where(Achievement.user_id == user.id, Achievement.key == "champion"))
    return {
        "first_prompt": count(select(func.count(Conversation.id)).where(Conversation.user_id == user.id)),
        "comparer": count(select(func.count(UsageEvent.id)).where(UsageEvent.user_id == user.id, UsageEvent.feature == "compare")),
        "smart_saver": int(savings >= 1.0),
        "agent_runner": count(select(func.count(Run.id)).where(Run.user_id == user.id, Run.status == "completed")),
        "reviewer": reviewed,
        "builder": count(select(func.count(CustomAgent.id)).where(CustomAgent.user_id == user.id)),
        "librarian": int(biggest_space),
        "evaluator": count(select(func.count(EvalRun.id)).where(EvalRun.user_id == user.id, EvalRun.status == "completed")),
        "canary_keeper": canaries,
        "notebook": count(select(func.count(UsageEvent.id)).where(UsageEvent.user_id == user.id, UsageEvent.feature == "notebook")),
        "publisher": count(select(func.count(ShowcaseItem.id)).where(ShowcaseItem.owner_id == user.id)),
        "champion": wins,
    }


def achievements_for(db: Session, user: User) -> list[dict]:
    """Unlock anything the evidence supports, record first unlock time, return every badge with progress."""
    progress = progress_for(db, user)
    unlocked = {a.key: a for a in db.scalars(select(Achievement).where(Achievement.user_id == user.id)).all()}
    changed = False
    for a in ACHIEVEMENTS:
        if a["key"] not in unlocked and progress.get(a["key"], 0) >= a["target"]:
            row = Achievement(user_id=user.id, key=a["key"])
            db.add(row)
            unlocked[a["key"]] = row
            changed = True
    if changed:
        db.commit()
    return [{**a, "progress": min(progress.get(a["key"], 0), a["target"]), "unlocked": a["key"] in unlocked, "unlocked_at": unlocked[a["key"]].unlocked_at.isoformat() if a["key"] in unlocked and unlocked[a["key"]].unlocked_at else None} for a in ACHIEVEMENTS]


# ---------------------------------------------------------------- leaderboard ----------------------------------------------------------------

def _blank_stats() -> dict:
    return {"requests": 0, "cost_usd": 0.0, "savings_usd": 0.0, "outcomes": 0, "agents": 0, "suites": 0, "likes": 0, "achievements": 0, "challenge_wins": 0, "_pr": []}


def leaderboard(db: Session, days: int = 30, by: str = "user") -> list[dict]:
    since = datetime.now(UTC) - timedelta(days=days)
    users = {u.id: u for u in db.scalars(select(User)).all()}
    stats: dict[str, dict] = defaultdict(_blank_stats)
    for e in db.scalars(select(UsageEvent).where(UsageEvent.created_at >= since)).all():
        s = stats[e.user_id]
        s["requests"] += 1
        s["cost_usd"] += e.cost_usd
        s["savings_usd"] += e.savings_usd or 0.0
    for r in db.scalars(select(Run).where(Run.created_at >= since, Run.status == "completed")).all():
        stats[r.user_id]["outcomes"] += 1
    for uid, n in db.execute(select(CustomAgent.user_id, func.count()).group_by(CustomAgent.user_id)).all():
        stats[uid]["agents"] += n
    for uid, n in db.execute(select(EvalSuite.owner_id, func.count()).where(EvalSuite.owner_id.is_not(None)).group_by(EvalSuite.owner_id)).all():
        stats[uid]["suites"] += n
    for uid, n in db.execute(select(ShowcaseItem.owner_id, func.sum(ShowcaseItem.likes)).group_by(ShowcaseItem.owner_id)).all():
        stats[uid]["likes"] += int(n or 0)
    for uid, key in db.execute(select(Achievement.user_id, Achievement.key)).all():
        stats[uid]["achievements"] += 1
        if key == "champion":
            stats[uid]["challenge_wins"] += 1
    for er in db.scalars(select(EvalRun).where(EvalRun.created_at >= since, EvalRun.status == "completed")).all():
        stats[er.user_id]["_pr"].append(float((er.summary or {}).get("pass_rate") or 0))
    rows = []
    for uid, s in stats.items():
        u = users.get(uid)
        pr = round(sum(s["_pr"]) / len(s["_pr"]), 1) if s["_pr"] else None
        points = sum(POINTS[k] * s[k] for k in POINTS)
        rows.append({"user_id": uid, "name": u.name if u else uid, "department": u.department if u else "Unknown", "role": u.role if u else "", **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items() if not k.startswith("_")}, "pass_rate": pr, "points": round(points, 1)})
    if by == "department":
        agg: dict[str, dict] = defaultdict(lambda: {"department": "", "people": 0, "requests": 0, "cost_usd": 0.0, "savings_usd": 0.0, "outcomes": 0, "agents": 0, "suites": 0, "likes": 0, "achievements": 0, "challenge_wins": 0, "points": 0.0, "_pr": []})
        for r in rows:
            d = agg[r["department"]]
            d["department"] = r["department"]
            d["people"] += 1
            for k in ("requests", "cost_usd", "savings_usd", "outcomes", "agents", "suites", "likes", "achievements", "challenge_wins", "points"):
                d[k] += r[k]
            if r["pass_rate"] is not None:
                d["_pr"].append(r["pass_rate"])
        rows = [{**{k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items() if not k.startswith("_")}, "pass_rate": round(sum(d["_pr"]) / len(d["_pr"]), 1) if d["_pr"] else None} for d in agg.values()]
    rows.sort(key=lambda r: -r["points"])
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows
