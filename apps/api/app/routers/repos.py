"""Popular Git repos: a curated, categorised snapshot refreshed by scripts/import_repos.py and committed."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, Query

from app.auth import current_user
from app.models import User

router = APIRouter(prefix="/v1/repos", tags=["repos"])
SNAPSHOT = Path(__file__).resolve().parents[2] / "catalog" / "repos.json"
CATEGORY_ORDER = ["Reference implementations", "Agent frameworks and SDKs", "Harnesses and skills", "Visual builders", "MCP", "Knowledge tooling", "Evaluation and observability"]
CATEGORY_BLURB = {
    "Reference implementations": "Public repositories by the playground's author that build these patterns for real. Read them, rate them in the Showcase, borrow what fits.",
    "Agent frameworks and SDKs": "The runtimes the framework flavors target.",
    "Harnesses and skills": "Where the role agents, personas, topologies and skills in the catalog come from, and the harnesses worth studying.",
    "Visual builders": "The low-code studios the playground exports to, and their neighbours.",
    "MCP": "Reference servers, the official registry and vendor catalogs behind the MCP Marketplace.",
    "Knowledge tooling": "Parsing, crawling and graph tooling that pairs with Knowledge Spaces.",
    "Evaluation and observability": "Evaluation harnesses and tracing platforms that complement the Evaluate and Operate pages.",
}


@lru_cache(maxsize=1)
def load_snapshot() -> dict:
    if not SNAPSHOT.exists():
        return {"generated_at": None, "repos": []}
    return json.loads(SNAPSHOT.read_text())


@router.get("")
def list_repos(category: str = Query(default=""), q: str = Query(default=""), _: User = Depends(current_user)) -> dict:
    snap = load_snapshot()
    rows = snap["repos"]
    if category:
        rows = [r for r in rows if r["category"] == category]
    if q:
        needle = q.lower()
        rows = [r for r in rows if needle in f"{r['full_name']} {r['blurb']} {' '.join(r.get('topics', []))}".lower()]
    counts: dict[str, int] = {}
    for r in snap["repos"]:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    return {
        "repos": rows, "total": len(snap["repos"]), "generated_at": snap["generated_at"],
        "categories": [{"id": c, "count": counts.get(c, 0), "blurb": CATEGORY_BLURB.get(c, "")} for c in CATEGORY_ORDER if counts.get(c)],
        "stars_total": sum(r["stars"] for r in snap["repos"]),
    }
