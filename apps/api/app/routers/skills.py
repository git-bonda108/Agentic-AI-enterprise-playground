from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import current_user
from app.models import User
from app.skills import get_skill, public_view, search_skills, stats

router = APIRouter(prefix="/v1/skills", tags=["skills"])


@router.get("")
def list_skills(q: str = Query(default=""), source: str = Query(default=""), category: str = Query(default=""), limit: int = Query(default=200, le=500), _: User = Depends(current_user)) -> dict:
    rows = search_skills(q=q, source=source, category=category, limit=limit)
    return {"skills": rows, "total": len(rows), "stats": stats()}


@router.get("/stats")
def skill_stats(_: User = Depends(current_user)) -> dict:
    return stats()


@router.get("/{skill_id}")
def read_skill(skill_id: str, _: User = Depends(current_user)) -> dict:
    s = get_skill(skill_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Unknown skill")
    return public_view(s, include_body=True)
