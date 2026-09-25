"""Skills: SKILL.md packs imported from public repositories, searchable and attachable to any agent."""

from __future__ import annotations

import json
from functools import lru_cache

from app.config import API_DIR

SKILLS_FILE = API_DIR / "catalog" / "skills.json"


@lru_cache(maxsize=1)
def load_skills() -> list[dict]:
    if not SKILLS_FILE.exists():
        return []
    return json.loads(SKILLS_FILE.read_text())


def by_id() -> dict[str, dict]:
    return {s["id"]: s for s in load_skills()}


def get_skill(skill_id: str) -> dict | None:
    return by_id().get(skill_id)


def public_view(skill: dict, include_body: bool = False) -> dict:
    view = {k: v for k, v in skill.items() if k != "body"}
    view["preview"] = skill.get("body", "")[:400]
    if include_body:
        view["body"] = skill.get("body", "")
    return view


def search_skills(q: str = "", source: str = "", category: str = "", limit: int = 200) -> list[dict]:
    rows = load_skills()
    if source:
        rows = [r for r in rows if r["source"]["title"] == source]
    if category:
        rows = [r for r in rows if r["category"] == category]
    if q:
        needle = q.lower()
        scored = []
        for r in rows:
            hay = f"{r['name']} {r['description']} {' '.join(r['tags'])}".lower()
            score = (3 if needle in r["name"].lower() else 0) + (2 if needle in r["description"].lower() else 0) + (1 if needle in hay else 0) + (1 if needle in r.get("body", "")[:2000].lower() else 0)
            if score:
                scored.append((score, r))
        scored.sort(key=lambda t: (-t[0], t[1]["name"]))
        rows = [r for _, r in scored]
    return [public_view(r) for r in rows[:limit]]


def stats() -> dict:
    rows = load_skills()
    cats: dict[str, int] = {}
    sources: dict[str, int] = {}
    for r in rows:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
        sources[r["source"]["title"]] = sources.get(r["source"]["title"], 0) + 1
    return {"total": len(rows), "by_category": dict(sorted(cats.items(), key=lambda kv: -kv[1])), "by_source": sources}


def skill_prompt(skill_ids: list[str], max_chars: int = 12000) -> str:
    """Skill bodies concatenated for a system prompt, trimmed to a character budget."""
    parts = []
    used = 0
    for sid in skill_ids:
        s = get_skill(sid)
        if not s:
            continue
        room = max_chars - used
        if room <= 200:
            break
        text = s.get("body", "")[:room]
        parts.append(f"## Skill: {s['name']}\n{s['description']}\n\n{text}")
        used += len(text)
    return "\n\n".join(parts)
