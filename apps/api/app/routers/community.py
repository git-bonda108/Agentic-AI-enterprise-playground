from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.core import REGISTRY
from app.auth import current_user
from app.catalog_store import get_entry
from app.community import (
    ACHIEVEMENTS,
    POINTS,
    achievements_for,
    challenge_payload,
    close_challenge,
    judge_submission,
    leaderboard,
    showcase_payload,
    toggle_like,
)
from app.db import get_db
from app.governance import check_budget
from app.models import (
    Challenge,
    ChallengeSubmission,
    Conversation,
    CustomAgent,
    EvalSuite,
    Run,
    ShowcaseComment,
    ShowcaseItem,
    User,
)

router = APIRouter(prefix="/v1/community", tags=["community"])


class ShowcaseBody(BaseModel):
    kind: str = Field(pattern="^(agent|run|conversation|suite)$")
    ref_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=3, max_length=140)
    summary: str = Field(default="", max_length=2000)
    outcome: str = Field(default="", max_length=300)
    tags: list[str] = Field(default_factory=list)


class DraftBody(BaseModel):
    run_id: str | None = None
    text: str | None = Field(default=None, max_length=2000)


class CommentBody(BaseModel):
    body: str = Field(min_length=1, max_length=1000)


class ChallengeBody(BaseModel):
    title: str = Field(min_length=3, max_length=140)
    brief: str = Field(min_length=10, max_length=4000)
    cases: list[dict] = Field(default_factory=list)
    rubric: dict = Field(default_factory=lambda: {"criteria": [{"id": "correctness", "weight": 1}, {"id": "completeness", "weight": 1}], "pass_threshold": 3.0})
    badge: str = Field(default="Challenge winner", max_length=80)
    days_open: int = Field(default=7, ge=1, le=90)


class SubmitBody(BaseModel):
    agent_id: str
    note: str = Field(default="", max_length=400)


def _ref_exists(db: Session, kind: str, ref_id: str, user: User) -> bool:
    if kind == "agent":
        return ref_id in REGISTRY or db.get(CustomAgent, ref_id) is not None or get_entry(ref_id) is not None
    if kind == "run":
        r = db.get(Run, ref_id)
        return r is not None and (r.user_id == user.id or user.role == "admin")
    if kind == "conversation":
        c = db.get(Conversation, ref_id)
        return c is not None and c.user_id == user.id
    return db.get(EvalSuite, ref_id) is not None


# ---------------------------------------------------------------- showcase ----------------------------------------------------------------

@router.get("/showcase")
def list_showcase(q: str = Query(default=""), tag: str = Query(default=""), sort: str = Query(default="new"), limit: int = Query(default=60, le=200), user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    everything = db.scalars(select(ShowcaseItem)).all()
    rows = everything
    if q:
        n = q.lower()
        rows = [r for r in rows if n in f"{r.title} {r.summary} {r.outcome} {' '.join(r.tags or [])}".lower()]
    if tag:
        rows = [r for r in rows if tag in (r.tags or [])]
    rows = sorted(rows, key=(lambda r: (-r.likes, -r.views, r.created_at.timestamp())) if sort == "top" else (lambda r: -r.created_at.timestamp()))
    tags: dict[str, int] = {}
    for r in everything:
        for t in r.tags or []:
            tags[t] = tags.get(t, 0) + 1
    return {"items": [showcase_payload(r, db, user) for r in rows[:limit]], "tags": dict(sorted(tags.items(), key=lambda kv: -kv[1])[:20]), "total": len(rows)}


@router.post("/showcase", status_code=201)
def publish(body: ShowcaseBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    if not _ref_exists(db, body.kind, body.ref_id, user):
        raise HTTPException(status_code=404, detail="That item does not exist or is not yours to publish")
    item = ShowcaseItem(owner_id=user.id, kind=body.kind, ref_id=body.ref_id, title=body.title, summary=body.summary, outcome=body.outcome, tags=[t.strip().lower()[:24] for t in body.tags if t.strip()][:6])
    db.add(item)
    db.commit()
    achievements_for(db, user)
    return showcase_payload(item, db, user)


@router.post("/showcase/draft")
def draft_post(body: DraftBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """The showcase-writer platform agent drafts the post; the person edits before publishing."""
    from app.agents.runtime import start_run

    if not body.run_id and not body.text:
        raise HTTPException(status_code=400, detail="Give a run id or a sentence")
    budget = check_budget(db, user)
    if not budget.allowed:
        raise HTTPException(status_code=402, detail=budget.reason)
    run = Run(blueprint_id="showcase-writer", user_id=user.id, input={"run_id": body.run_id, "text": body.text}, status="queued")
    db.add(run)
    db.commit()
    start_run(run, background=False)
    db.expire_all()
    run = db.get(Run, run.id)
    if run.status != "completed":
        raise HTTPException(status_code=502, detail=run.error or "Draft failed")
    return {"draft": run.output, "run_id": run.id, "cost_usd": run.cost_usd}


@router.get("/showcase/{item_id}")
def get_showcase(item_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    item = db.get(ShowcaseItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")
    item.views += 1
    db.commit()
    return showcase_payload(item, db, user, with_comments=True)


@router.post("/showcase/{item_id}/like")
def like(item_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    item = db.get(ShowcaseItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")
    liked = toggle_like(db, item, user)
    return {"liked": liked, "likes": item.likes}


@router.post("/showcase/{item_id}/comments", status_code=201)
def comment(item_id: str, body: CommentBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    item = db.get(ShowcaseItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")
    db.add(ShowcaseComment(item_id=item.id, user_id=user.id, body=body.body))
    db.commit()
    return showcase_payload(item, db, user, with_comments=True)


@router.delete("/showcase/{item_id}", status_code=204)
def unpublish(item_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    item = db.get(ShowcaseItem, item_id)
    if item is None or (item.owner_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(item)
    db.commit()


# ---------------------------------------------------------------- challenges ----------------------------------------------------------------

@router.get("/challenges")
def list_challenges(_: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(Challenge).order_by(Challenge.status.desc(), Challenge.created_at.desc())).all()
    return {"challenges": [challenge_payload(c, db) for c in rows]}


@router.post("/challenges", status_code=201)
def create_challenge(body: ChallengeBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    if user.role not in ("admin", "champion"):
        raise HTTPException(status_code=403, detail="Admins and champions run challenges")
    if not body.cases:
        raise HTTPException(status_code=400, detail="Add at least one shared case so every entry is judged the same way")
    c = Challenge(owner_id=user.id, title=body.title, brief=body.brief, cases=body.cases, rubric=body.rubric, badge=body.badge, ends_at=datetime.now(UTC) + timedelta(days=body.days_open))
    db.add(c)
    db.commit()
    return challenge_payload(c, db)


@router.get("/challenges/{challenge_id}")
def get_challenge(challenge_id: str, _: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    c = db.get(Challenge, challenge_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return challenge_payload(c, db)


@router.post("/challenges/{challenge_id}/submit", status_code=201)
def submit(challenge_id: str, body: SubmitBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    c = db.get(Challenge, challenge_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if c.status != "open":
        raise HTTPException(status_code=409, detail="This challenge is closed")
    runnable = body.agent_id in REGISTRY or (get_entry(body.agent_id) or {}).get("runnable")
    if not runnable:
        raise HTTPException(status_code=404, detail="Unknown or non-runnable agent")
    existing = db.scalar(select(ChallengeSubmission).where(ChallengeSubmission.challenge_id == c.id, ChallengeSubmission.user_id == user.id))
    if existing:
        existing.agent_id, existing.note, existing.score, existing.judged, existing.eval_run_id = body.agent_id, body.note, None, None, None
    else:
        db.add(ChallengeSubmission(challenge_id=c.id, user_id=user.id, agent_id=body.agent_id, note=body.note))
    db.commit()
    return challenge_payload(c, db)


@router.post("/challenges/{challenge_id}/judge")
def judge(challenge_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    c = db.get(Challenge, challenge_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if user.role != "admin" and c.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the challenge owner or an admin can judge")
    budget = check_budget(db, user)
    if not budget.allowed:
        raise HTTPException(status_code=402, detail=budget.reason)
    pending = db.scalars(select(ChallengeSubmission).where(ChallengeSubmission.challenge_id == c.id, ChallengeSubmission.score.is_(None))).all()
    for s in pending:
        judge_submission(db, c, s)
    return {**challenge_payload(c, db), "judged_now": len(pending)}


@router.post("/challenges/{challenge_id}/close")
def close(challenge_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    c = db.get(Challenge, challenge_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if user.role != "admin" and c.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the challenge owner or an admin can close")
    return close_challenge(db, c)


# ---------------------------------------------------------------- achievements and leaderboard ----------------------------------------------------------------

@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    badges = achievements_for(db, user)
    board = leaderboard(db, days=30)
    mine = next((r for r in board if r["user_id"] == user.id), None)
    return {"achievements": badges, "unlocked": sum(1 for b in badges if b["unlocked"]), "total": len(ACHIEVEMENTS), "rank": mine["rank"] if mine else None, "points": mine["points"] if mine else 0, "people": len(board)}


@router.get("/leaderboard")
def board(by: str = Query(default="user", pattern="^(user|department)$"), days: int = Query(default=30, ge=1, le=365), user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    achievements_for(db, user)  # keep the caller's badges fresh before ranking
    return {"by": by, "days": days, "rows": leaderboard(db, days=days, by=by), "points": POINTS}
