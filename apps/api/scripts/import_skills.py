"""Import SKILL.md packs from public repositories into apps/api/catalog/skills.json.

Run once (network required): `uv run python scripts/import_skills.py`. The output is committed, so the API never fetches at runtime.
Sources and licences: everything-claude-code (MIT), ruflo (MIT).
"""

from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_catalog import fetch, parse_frontmatter, slug, tree

OUT = Path(__file__).resolve().parent.parent / "catalog" / "skills.json"
MAX_BODY = 6000

SOURCES = {
    "ecc": {"repo": "affaan-m/everything-claude-code", "license": "MIT", "title": "everything-claude-code", "pattern": r"^skills/[^/]+/SKILL\.md$"},
    # ruflo wraps its agents as `agent-*` skills; those are already in the agent catalog, so only the real skills are taken.
    "ruflo": {"repo": "ruvnet/ruflo", "license": "MIT", "title": "ruflo", "pattern": r"^\.agents/skills/(?!agent-)[^/]+/SKILL\.md$"},
}

CATEGORIES = [
    ("Testing and quality", r"test|tdd|qa\b|quality|lint|coverage|e2e|playwright|regression"),
    ("Security", r"secur|threat|vuln|owasp|secret|compliance|audit"),
    ("Review and planning", r"review|plan|spec|design doc|architect|rfc|estimate"),
    ("Data and analytics", r"\bsql\b|data|analytic|pandas|etl|warehouse|dbt|spark"),
    ("Documents and writing", r"docx|pptx|xlsx|pdf|markdown|writing|doc(ument)?s?\b|readme|report"),
    ("AI and agents", r"agent|prompt|llm|rag|embedding|mcp|eval|model|swarm|orchestr"),
    ("Cloud and operations", r"deploy|kubernetes|docker|terraform|aws|azure|gcp|ci/cd|pipeline|devops|monitor|incident"),
    ("Frontend and mobile", r"react|next\.?js|frontend|css|tailwind|ios|android|flutter|swift|ui\b"),
    ("Backend and languages", r"python|typescript|golang|\bgo\b|rust|java|c\+\+|c#|php|api|backend|django|fastapi"),
    ("Product and business", r"product|marketing|seo|growth|customer|sales|pricing|strategy"),
]


def categorize(text: str) -> str:
    low = text.lower()
    for name, pattern in CATEGORIES:
        if re.search(pattern, low):
            return name
    return "General"


def build(source: str, cfg: dict, path: str, text: str) -> dict | None:
    meta, body = parse_frontmatter(text)
    folder = path.split("/")[-2]
    name = meta.get("name") or folder
    description = (meta.get("description") or "").strip()
    if not description:
        for line in body.splitlines():
            line = line.strip().lstrip("#").strip()
            if len(line) > 30 and not line.startswith(("```", "|", "-", "*")):
                description = line
                break
    if len(body) < 120:
        return None
    pretty = name.replace("-", " ").replace("_", " ").strip()
    pretty = pretty[:1].upper() + pretty[1:]
    return {
        "id": f"{source}-{slug(folder)}",
        "name": pretty,
        "description": description[:400],
        "source": {"repo": cfg["repo"], "path": path, "license": cfg["license"], "url": f"https://github.com/{cfg['repo']}/blob/main/{path}", "title": cfg["title"]},
        "body": body[:MAX_BODY],
        "body_truncated": len(body) > MAX_BODY,
        "category": categorize(f"{name} {description} {body[:1500]}"),
        "tags": sorted({source, *(t.strip() for t in re.split(r"[,\s]+", meta.get("tags", "")) if t.strip())}),
        "words": len(body.split()),
    }


def main() -> None:
    all_rows: list[dict] = []
    for source, cfg in SOURCES.items():
        paths = [p for p in tree(cfg["repo"]) if re.search(cfg["pattern"], p)]
        print(f"{source}: {len(paths)} skill files", file=sys.stderr)
        with ThreadPoolExecutor(max_workers=8) as pool:
            texts = list(pool.map(lambda p, repo=cfg["repo"]: fetch(repo, p), paths))
        seen: set[str] = set()
        for path, text in zip(paths, texts, strict=True):
            row = build(source, cfg, path, text)
            if row and row["id"] not in seen:
                seen.add(row["id"])
                all_rows.append(row)
    all_rows.sort(key=lambda r: (r["category"], r["name"]))
    OUT.write_text(json.dumps(all_rows, indent=1, ensure_ascii=False))
    print(f"wrote {len(all_rows)} -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
