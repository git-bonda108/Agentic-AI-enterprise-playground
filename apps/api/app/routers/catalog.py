from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_user
from app.catalog_store import FAMILIES, custom_entry, get_entry, load_entries, public_view, stats
from app.curator import curate
from app.db import get_db
from app.models import CustomAgent, User
from app.routers.admin import require_admin

router = APIRouter(prefix="/v1/catalog", tags=["catalog"])


@router.get("")
def list_catalog(
    family: str = Query(default=""), q: str = Query(default=""), source: str = Query(default=""), runnable: bool | None = Query(default=None),
    status: str = Query(default=""), limit: int = Query(default=300, le=500), user: User = Depends(current_user), db: Session = Depends(get_db),
) -> dict:
    mine = db.scalars(select(CustomAgent).where((CustomAgent.user_id == user.id) | (CustomAgent.published.is_(True)))).all()
    rows = [public_view(custom_entry(a)) for a in mine] + [public_view(e) for e in load_entries()]
    if family:
        rows = [r for r in rows if r["family"] == family]
    if source:
        rows = [r for r in rows if r["source"]["title"] == source]
    if runnable is not None:
        rows = [r for r in rows if r["runnable"] == runnable]
    if status:
        rows = [r for r in rows if r["curation"]["status"] == status]
    if q:
        needle = q.lower()
        rows = [r for r in rows if needle in f"{r['name']} {r['summary']} {' '.join(r['tags'])} {r.get('group', '')}".lower()]
    return {"entries": rows[:limit], "total": len(rows), "families": FAMILIES, "stats": stats()}


@router.get("/stats")
def catalog_stats(_: User = Depends(current_user)) -> dict:
    return stats()


@router.get("/{entry_id}")
def get_catalog_entry(entry_id: str, _: User = Depends(current_user)) -> dict:
    entry = get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Unknown catalog entry")
    return public_view(entry, include_instructions=True)


@router.post("/curate")
def run_curator(_: User = Depends(require_admin)) -> dict:
    rows = curate()
    return {"reviewed": len(rows), "green": sum(1 for r in rows if r["status"] == "green"), "red": sum(1 for r in rows if r["status"] == "red")}
