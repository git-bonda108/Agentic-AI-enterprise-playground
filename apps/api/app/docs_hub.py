"""The documentation hub: the product guides served inside the playground, so nothing points at the private repository.

The guides live in the repository's `docs/` folder and are mirrored into `apps/api/catalog/docs` by `scripts/sync-docs.sh`
(the API image is built from `apps/api`, so the mirror is what ships). Locally the repository copy wins when it exists.
Each guide carries a slug, a section, a one-line summary, the product page it belongs with, its headings and a reading time;
`search()` finds the paragraphs that mention a query. The delivery log stays internal and is never listed.
"""

from __future__ import annotations

import re
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_CATALOG_DOCS = _HERE.parent / "catalog" / "docs"
# The repository checkout keeps the guides three levels up (apps/api/app -> docs); inside the container the package sits at
# /app/app with nothing above it, so the mirror in catalog/docs is the only copy there.
_REPO_DOCS = _HERE.parents[2] / "docs" if len(_HERE.parents) > 2 else _CATALOG_DOCS

START, BUILD, OPERATE, PLATFORM = "Start here", "Build", "Operate", "Platform"

GUIDES: list[dict] = [
    {"slug": "tour", "file": "DEMO_SCRIPT.md", "title": "Guided tour", "section": START, "summary": "Every capability in the order a first walk-through flows, with what to click and what you should see.", "page": "/home", "page_label": "Console"},
    {"slug": "workflows", "file": "WORKFLOWS.md", "title": "Workflows", "section": START, "summary": "How people use the playground day to day, and how it is built, tested and shipped.", "page": "/build/playground", "page_label": "Playground"},
    {"slug": "agents", "file": "AGENTS.md", "title": "Agents", "section": BUILD, "summary": "Run a blueprint, build your own in the wizard, or bring your own SDK through the gateway; tools, review gates and traces.", "page": "/build/agents", "page_label": "Agent Hub"},
    {"slug": "notebooks", "file": "NOTEBOOKS.md", "title": "Notebooks", "section": BUILD, "summary": "The gallery, the playground helper, browser and sandbox runtimes, package installs and notebook hours.", "page": "/build/notebooks", "page_label": "Notebooks"},
    {"slug": "datasets", "file": "DATASETS.md", "title": "Datasets", "section": BUILD, "summary": "The mock sets with their columns and provenance, trusted public sources, the cost drill-down and console hours.", "page": "/build/data", "page_label": "Datasets"},
    {"slug": "low-code", "file": "LOW_CODE.md", "title": "Two ways to build", "section": BUILD, "summary": "Gen AI and Agentic AI blueprints, the Langflow, n8n and Copilot Studio artefacts, and the low-code landscape.", "page": "/discover/low-code", "page_label": "Low-code studios"},
    {"slug": "marketplace", "file": "MARKETPLACE.md", "title": "MCP Marketplace and Popular Git repos", "section": BUILD, "summary": "Thousands of MCP servers with per-client configuration, and the repositories behind the playground.", "page": "/discover/connectors", "page_label": "MCP Marketplace"},
    {"slug": "cloud-platforms", "file": "CLOUD_PLATFORMS.md", "title": "Cloud platforms", "section": BUILD, "summary": "Foundry, AgentCore, Google Agent Runtime and Managed Agents: portals, CLI sign-in, framework fit and step-by-step deploy guides.", "page": "/discover/clouds", "page_label": "Cloud platforms"},
    {"slug": "api", "file": "API.md", "title": "API reference", "section": OPERATE, "summary": "Every route with its purpose, the identity headers, the OpenAI-compatible gateway, usage and traces.", "page": "/operate/traces", "page_label": "Traces"},
    {"slug": "retest", "file": "RETEST.md", "title": "Release verification", "section": OPERATE, "summary": "The page-by-page check of every left-pane item: what was verified, how, and the defects the retest found and fixed.", "page": "/home", "page_label": "Console"},
    {"slug": "architecture", "file": "ARCHITECTURE.md", "title": "Architecture", "section": PLATFORM, "summary": "The system as built and the Azure topology it runs on, for engineers who operate or extend it.", "page": "/admin/settings", "page_label": "Settings"},
    {"slug": "security", "file": "SECURITY.md", "title": "Security", "section": PLATFORM, "summary": "What protects the playground, layer by layer, and what a reviewer should verify.", "page": "/admin/policies", "page_label": "Policies"},
    {"slug": "deployment", "file": "DEPLOYMENT.md", "title": "Deployment", "section": PLATFORM, "summary": "What gets deployed on Azure, what it costs at pilot sizing, the one-command deploy and operations.", "page": "/discover/clouds", "page_label": "Cloud platforms"},
]
SECTIONS = [START, BUILD, OPERATE, PLATFORM]
WORDS_PER_MINUTE = 220


def docs_dir() -> Path:
    return _REPO_DOCS if (_REPO_DOCS / "API.md").exists() else _CATALOG_DOCS


def catalog_dir() -> Path:
    return _CATALOG_DOCS


def _read(file: str) -> str:
    return (docs_dir() / file).read_text(encoding="utf-8")


def slugify(text: str) -> str:
    s = re.sub(r"[`*_]", "", text.lower())
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    return re.sub(r"\s+", "-", s).strip("-")


def headings(markdown: str) -> list[dict]:
    """Second-level headings with the anchor ids the renderer produces."""
    out = []
    in_code = False
    for line in markdown.splitlines():
        if line.startswith("```"):
            in_code = not in_code
            continue
        if not in_code and line.startswith("## "):
            text = line[3:].strip()
            out.append({"text": text, "id": slugify(text)})
    return out


def _meta(g: dict, markdown: str) -> dict:
    words = len(re.findall(r"\w+", markdown))
    return {**g, "minutes": max(1, round(words / WORDS_PER_MINUTE)), "words": words, "headings": headings(markdown)}


def list_guides() -> list[dict]:
    return [_meta(g, _read(g["file"])) for g in GUIDES]


def get_guide(slug: str) -> dict:
    g = next((x for x in GUIDES if x["slug"] == slug), None)
    if g is None:
        raise KeyError(slug)
    markdown = _read(g["file"])
    i = [x["slug"] for x in GUIDES].index(slug)
    prev_g = GUIDES[i - 1] if i > 0 else None
    next_g = GUIDES[i + 1] if i + 1 < len(GUIDES) else None
    return {
        **_meta(g, markdown), "markdown": markdown,
        "prev": {"slug": prev_g["slug"], "title": prev_g["title"]} if prev_g else None,
        "next": {"slug": next_g["slug"], "title": next_g["title"]} if next_g else None,
    }


def file_slugs() -> dict[str, str]:
    """Markdown file name to slug, so relative links between guides resolve inside the hub."""
    return {g["file"]: g["slug"] for g in GUIDES}


def image_path(name: str) -> Path | None:
    if not re.fullmatch(r"[a-z0-9._-]+\.(png|jpg|jpeg|svg|gif)", name) or ".." in name:
        return None
    path = docs_dir() / "images" / name
    return path if path.exists() else None


def search(query: str, limit: int = 20) -> list[dict]:
    """Paragraphs that contain every word of the query, ranked by how many times the words appear."""
    words = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 1]
    if not words:
        return []
    hits: list[dict] = []
    for g in GUIDES:
        markdown = _read(g["file"])
        section = ""
        for para in re.split(r"\n\s*\n", markdown):
            stripped = para.strip()
            if stripped.startswith("## "):
                section = stripped[3:].strip()
            text = re.sub(r"\s+", " ", re.sub(r"[`#*|>]", "", stripped))
            low = text.lower()
            if all(w in low for w in words):
                score = sum(low.count(w) for w in words)
                first = min(low.find(w) for w in words)
                start = max(0, first - 80)
                snippet = ("…" if start else "") + text[start:start + 220] + ("…" if len(text) > start + 220 else "")
                hits.append({"slug": g["slug"], "title": g["title"], "section": section, "anchor": slugify(section) if section else "", "snippet": snippet, "score": score})
    hits.sort(key=lambda h: -h["score"])
    return hits[:limit]
