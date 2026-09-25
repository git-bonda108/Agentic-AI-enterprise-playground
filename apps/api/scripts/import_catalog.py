"""Import agent definitions from public repositories into apps/api/catalog/*.json.

Run once (network required): `uv run python scripts/import_catalog.py`. The output is committed, so the API never fetches at runtime.
Sources and licenses: everything-claude-code (MIT), gstack (MIT), ruflo (MIT).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "catalog"
MAX_BODY = 3500

SOURCES = {
    "ecc": {"repo": "affaan-m/everything-claude-code", "license": "MIT", "family": "Role", "pattern_glob": r"^agents/[^/]+\.md$", "title": "everything-claude-code"},
    "gstack": {"repo": "garrytan/gstack", "license": "MIT", "family": "Persona", "pattern_glob": r"SKILL\.md$", "title": "gstack"},
    "ruflo": {"repo": "ruvnet/ruflo", "license": "MIT", "family": "Topology", "pattern_glob": r"^\.claude/agents/(core|swarm|hive-mind|consensus|sparc|optimization|analysis|reasoning|goal|development|documentation|devops|testing|specialized)/.*\.md$", "title": "ruflo"},
}
EXCLUDE = re.compile(r"test|fixture|node_modules|openclaw|README|/index\.md$|^SKILL\.md$|^(ios-|setup-|sync-|gstack-upgrade|context-|open-gstack|skillify|freeze|unfreeze|guard|careful|health|make-pdf|deslop|codex|pair-agent|learn/)", re.IGNORECASE)


def gh(args: list[str]) -> str:
    return subprocess.run(["gh", "api", *args], check=True, capture_output=True, text=True).stdout


def tree(repo: str) -> list[str]:
    branch = gh([f"repos/{repo}", "--jq", ".default_branch"]).strip()
    return gh([f"repos/{repo}/git/trees/{branch}?recursive=1", "--jq", ".tree[].path"]).splitlines()


def fetch(repo: str, path: str) -> str:
    return gh([f"repos/{repo}/contents/{path}", "-H", "Accept: application/vnd.github.raw"])


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw, body = text[3:end], text[end + 4 :]
    meta: dict = {}
    key: str | None = None
    for line in raw.splitlines():
        if line and not line.startswith((" ", "\t")) and ":" in line:
            key, value = line.split(":", 1)
            key, value = key.strip(), value.strip()
            if value in ("|", ">", "|-", ">-", ""):
                meta[key] = ""  # block scalar or list follows
            else:
                meta[key] = value.strip('"').strip("'")
        elif key is not None and line.strip():
            item = line.strip()
            if item.startswith("- "):
                meta[key] = (meta[key] + ", " if meta[key] else "") + item[2:].strip().strip('"')
            else:
                meta[key] = (meta[key] + " " if meta[key] else "") + item
    return meta, body.strip()


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def summarize(body: str, meta: dict) -> str:
    desc = meta.get("description", "")
    if desc:
        return desc[:280]
    for line in body.splitlines():
        line = line.strip().lstrip("#").strip()
        if len(line) > 40 and not line.startswith(("```", "|", "-", "*")):
            return line[:280]
    return "Imported agent definition"


def tools_of(meta: dict) -> list[str]:
    raw = meta.get("tools", "") or meta.get("allowed-tools", "")
    return [t.strip() for t in re.split(r"[,\s]+", raw) if t.strip()] if raw else []


def build_entry(source: str, cfg: dict, path: str, text: str) -> dict:
    meta, body = parse_frontmatter(text)
    name = meta.get("name") or Path(path).parent.name if path.endswith("SKILL.md") else meta.get("name") or Path(path).stem
    name = name.replace("-", " ").replace("_", " ").strip().title() if name.islower() or "-" in name else name
    group = path.split("/")[2] if source == "ruflo" and path.count("/") >= 3 else ""
    return {
        "id": f"{source}-{slug(meta.get('name') or Path(path).stem if not path.endswith('SKILL.md') else Path(path).parent.name)}",
        "name": name,
        "family": cfg["family"],
        "source": {"repo": cfg["repo"], "path": path, "license": cfg["license"], "url": f"https://github.com/{cfg['repo']}/blob/main/{path}", "title": cfg["title"]},
        "group": group,
        "summary": summarize(body, meta),
        "instructions": body[:MAX_BODY],
        "instructions_truncated": len(body) > MAX_BODY,
        "tools": tools_of(meta),
        "model_hint": meta.get("model", ""),
        "tags": sorted({t for t in [group, source, *(meta.get("tags", "").split(",") if meta.get("tags") else [])] if t}),
        "runnable": True,
        "tier": "Workhorse",
    }


def import_source(source: str, cfg: dict) -> list[dict]:
    paths = [p for p in tree(cfg["repo"]) if re.search(cfg["pattern_glob"], p) and not EXCLUDE.search(p)]
    print(f"{source}: {len(paths)} files", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=8) as pool:
        texts = list(pool.map(lambda p: fetch(cfg["repo"], p), paths))
    entries = []
    seen = set()
    for path, text in zip(paths, texts, strict=True):
        entry = build_entry(source, cfg, path, text)
        if entry["id"] in seen or len(entry["instructions"]) < 80:
            continue
        seen.add(entry["id"])
        entries.append(entry)
    return entries


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for source, cfg in SOURCES.items():
        entries = import_source(source, cfg)
        (OUT / f"{source}.json").write_text(json.dumps(entries, indent=1, ensure_ascii=False))
        print(f"wrote {len(entries)} -> catalog/{source}.json", file=sys.stderr)


if __name__ == "__main__":
    main()
