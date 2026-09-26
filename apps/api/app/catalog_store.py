"""The blueprint catalog: imported agent definitions, authored low-code templates and cloud sample mirrors, plus curation results."""

from __future__ import annotations

import json
from functools import lru_cache

from app.catalog_authored import CLOUD_MIRRORS, LOWCODE_TEMPLATES
from app.config import API_DIR

CATALOG_DIR = API_DIR / "catalog"
FAMILIES = ["Domain", "Role", "Topology", "Persona", "Low-code", "Cloud"]
PROMPT_AGENT_GRAPH = {
    "nodes": [{"id": "prepare", "label": "Prepare context", "kind": "tool"}, {"id": "respond", "label": "Agent responds", "kind": "llm"}, {"id": "check", "label": "Output check", "kind": "gate"}],
    "edges": [["prepare", "respond"], ["respond", "check"]],
    "columns": [["prepare"], ["respond"], ["check"]],
}


def _domain_entries() -> list[dict]:
    """The executable blueprints, presented as catalog entries so one page shows every family."""
    from app.agents.core import REGISTRY  # local import: the registry imports this module

    out = []
    for bp in REGISTRY.values():
        if bp.family != "Domain":  # platform agents run the playground itself and live in the Agent Hub, not the catalog
            continue
        out.append({
            "id": bp.id, "name": bp.name, "family": "Domain", "group": bp.pattern,
            "source": {"repo": "playground", "path": f"app/agents/blueprints/{bp.id.replace('-', '_')}.py", "license": "MIT", "url": bp.links.get("origin", "https://github.com/git-bonda108"), "title": "Playground blueprints"},
            "summary": bp.summary, "instructions": bp.description, "instructions_truncated": False, "tools": list(bp.datasets), "model_hint": "",
            "tags": ["domain", *bp.flavors], "runnable": True, "tier": next((t for t in bp.tiers.values() if t in ("Economy", "Workhorse", "Premium")), "Workhorse"),
            "samples": bp.samples, "input_schema": bp.input_schema, "flavors": bp.flavors, "links": bp.links, "knowledge": bp.datasets,
            "graph": bp.graph, "review_gates": bp.review_gates,  # the Gen AI / Agentic AI rule reads these
        })
    return out


@lru_cache(maxsize=1)
def load_entries() -> list[dict]:
    entries: list[dict] = list(_domain_entries())
    for name in ("ecc", "gstack", "ruflo"):
        path = CATALOG_DIR / f"{name}.json"
        if path.exists():
            entries.extend(json.loads(path.read_text()))
    entries.extend(LOWCODE_TEMPLATES)
    entries.extend(CLOUD_MIRRORS)
    return entries


@lru_cache(maxsize=1)
def load_curation() -> dict[str, dict]:
    path = CATALOG_DIR / "curation.json"
    if not path.exists():
        return {}
    return {row["id"]: row for row in json.loads(path.read_text())}


def by_id() -> dict[str, dict]:
    return {e["id"]: e for e in load_entries()}


def custom_entry(agent) -> dict:
    return {
        "id": agent.id, "name": agent.name, "family": "Low-code", "group": "yours",
        "source": {"repo": "playground", "path": f"custom/{agent.id}", "license": "Yours", "url": "/build/agents", "title": "Yours"},
        "summary": agent.description, "instructions": agent.instructions, "instructions_truncated": False, "tools": agent.tools or [], "model_hint": "",
        "tags": ["custom", "no-code"], "runnable": True, "tier": "Workhorse", "knowledge": agent.knowledge or [], "starter_prompts": agent.starters or [],
        "skills": agent.skills or [], "connectors": agent.tools or [], "builtin_tools": agent.builtin_tools or [],
        "flavors": ["No-code", "Copilot Studio export"], "samples": [{"name": s[:48], "input": {"task": s}} for s in (agent.starters or [])[:3]] or [{"name": "Ask", "input": {"task": "Describe what you do."}}],
        "links": {"export": f"/v1/custom-agents/{agent.id}/export/declarative-agent"}, "owner_id": agent.user_id, "published": agent.published,
    }


def get_entry(entry_id: str) -> dict | None:
    if entry_id.startswith("custom-"):
        from app.db import SessionLocal
        from app.models import CustomAgent

        with SessionLocal() as db:
            agent = db.get(CustomAgent, entry_id)
            return custom_entry(agent) if agent else None
    return by_id().get(entry_id)


def public_view(entry: dict, include_instructions: bool = False) -> dict:
    from app.lowcode import category_for

    cur = load_curation().get(entry["id"]) or ({"status": "green", "reasons": ["Built in the wizard"]} if entry["id"].startswith("custom-") else {"status": "unreviewed", "reasons": []})
    view = {k: v for k, v in entry.items() if k != "instructions"}
    view["category"] = category_for(entry)
    view["instructions_preview"] = entry.get("instructions", "")[:600]
    view["curation"] = cur
    if include_instructions:
        view["instructions"] = entry.get("instructions", "")
    return view


def manifest_for(entry: dict) -> dict:
    """A blueprint-style manifest so the run viewer can draw the generic prompt-agent graph for a catalog entry."""
    return {
        "id": entry["id"], "name": entry["name"], "family": entry["family"], "pattern": "Prompt agent with governed model policy" if entry["family"] != "Low-code" else "Instructions, knowledge, starter prompts",
        "summary": entry["summary"], "description": entry.get("description", entry["summary"]),
        "tiers": {"respond": entry.get("tier", "Workhorse")}, "graph": PROMPT_AGENT_GRAPH,
        "samples": entry.get("samples") or [{"name": "Ask the agent", "input": {"task": entry.get("starter_prompts", ["Describe what you do and how you would approach a typical task."])[0]}}],
        "datasets": entry.get("knowledge", []), "flavors": entry.get("flavors", ["LangGraph", "OpenAI Agents SDK", "Claude"]),
        "review_gates": [], "dashboard": ["Runs", "Cost per run"], "links": {"source": entry["source"]["url"], **entry.get("links", {})},
        "input_schema": {"task": "text", "context": "optional text"}, "batch": 4,
        "skills": entry.get("skills", []), "connectors": entry.get("connectors", []), "builtin_tools": entry.get("builtin_tools", []),
    }


def stats() -> dict:
    entries = load_entries()
    cur = load_curation()
    fam = {f: 0 for f in FAMILIES}
    for e in entries:
        fam[e["family"]] = fam.get(e["family"], 0) + 1
    from app.lowcode import CATEGORIES, category_for

    by_category = {c: 0 for c in CATEGORIES}
    for e in entries:
        by_category[category_for(e)] += 1
    return {
        "total": len(entries), "by_family": fam, "by_category": by_category,
        "green": sum(1 for e in entries if cur.get(e["id"], {}).get("status") == "green"),
        "red": sum(1 for e in entries if cur.get(e["id"], {}).get("status") == "red"),
        "runnable": sum(1 for e in entries if e.get("runnable")),
        "sources": sorted({e["source"]["title"] for e in entries}),
    }
