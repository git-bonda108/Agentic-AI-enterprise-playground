"""Documentation hub routes: the product guides, one guide with its markdown, images and full-text search."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.auth import current_user
from app.docs_hub import SECTIONS, file_slugs, get_guide, image_path, list_guides, search
from app.models import User

router = APIRouter(prefix="/v1/docs", tags=["docs"])


@router.get("")
def guides(_: User = Depends(current_user)) -> dict:
    return {"sections": SECTIONS, "guides": list_guides(), "files": file_slugs()}


@router.get("/search")
def search_guides(q: str = Query(min_length=1, max_length=120), _: User = Depends(current_user)) -> dict:
    return {"query": q, "hits": search(q)}


@router.get("/images/{name}")
def image(name: str, _: User = Depends(current_user)) -> FileResponse:
    path = image_path(name)
    if path is None:
        raise HTTPException(status_code=404, detail="Unknown image")
    return FileResponse(path)


@router.get("/{slug}")
def guide(slug: str, _: User = Depends(current_user)) -> dict:
    try:
        return {**get_guide(slug), "files": file_slugs()}
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown guide") from None
