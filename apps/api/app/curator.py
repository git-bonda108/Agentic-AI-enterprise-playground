"""The curator validates every catalog entry and records a green or red status with reasons."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from pydantic import BaseModel, Field, ValidationError

from app.catalog_store import CATALOG_DIR, FAMILIES, load_curation, load_entries

KNOWN_TOOLS = {"read", "write", "edit", "grep", "glob", "bash", "webfetch", "websearch", "askuserquestion", "task", "todowrite", "notebookedit", "knowledge", "mcp"}


class SourceModel(BaseModel):
    repo: str
    path: str
    license: str = Field(min_length=2)
    url: str = Field(pattern=r"^https://")
    title: str


class EntryModel(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9-]{3,80}$")
    name: str = Field(min_length=2, max_length=120)
    family: str
    source: SourceModel
    summary: str = Field(min_length=10, max_length=400)
    instructions: str = Field(min_length=40)
    tools: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    runnable: bool
    tier: str


def review(entry: dict) -> dict:
    reasons: list[str] = []
    try:
        model = EntryModel(**{k: entry.get(k) for k in EntryModel.model_fields if k in entry})
    except ValidationError as exc:
        reasons.extend(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()[:4])
        return {"id": entry.get("id", "?"), "status": "red", "reasons": reasons, "reviewed_at": datetime.now(UTC).isoformat()}
    if model.family not in FAMILIES:
        reasons.append(f"Unknown family {model.family}")
    if model.tier not in ("Economy", "Workhorse", "Premium", "Frontier"):
        reasons.append(f"Unknown tier {model.tier}")
    unknown_tools = [t for t in model.tools if t.lower().split("(")[0] not in KNOWN_TOOLS and not t.lower().startswith("mcp")]
    if len(unknown_tools) > 3:
        reasons.append(f"Many unknown tools: {', '.join(unknown_tools[:3])}")
    if model.runnable and len(model.instructions) < 120:
        reasons.append("Instructions too short to run")
    if entry.get("instructions_truncated") and model.family == "Topology":
        reasons.append("Instructions truncated at import; review the source before promoting")
    status = "red" if any(r.startswith(("Unknown", "Instructions too short")) for r in reasons) else "green"
    return {"id": model.id, "status": status, "reasons": reasons, "reviewed_at": datetime.now(UTC).isoformat()}


def curate(write: bool = True) -> list[dict]:
    rows = [review(e) for e in load_entries()]
    if write:
        CATALOG_DIR.mkdir(exist_ok=True)
        (CATALOG_DIR / "curation.json").write_text(json.dumps(rows, indent=1))
        load_curation.cache_clear()
    return rows


def ensure_curated() -> None:
    if not (CATALOG_DIR / "curation.json").exists():
        curate()
