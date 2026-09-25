"""The playground as an MCP server (streamable HTTP, JSON-RPC 2.0).

Clients such as Claude Desktop, Cursor or an agent built elsewhere can list models, read usage, run blueprints and search
Knowledge Spaces, always as a specific person, under that person's policy and budget.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.core import REGISTRY
from app.catalog import catalog_payload
from app.config import settings
from app.db import SessionLocal
from app.models import Run, User

SERVER_INFO = {"name": "enterprise-ai-playground", "version": "0.7.0"}
PROTOCOL_VERSION = "2025-06-18"

TOOLS: list[dict] = [
    {"name": "list_models", "description": "Models the caller may use, with tier, provider and price per million tokens.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "usage_summary", "description": "The caller's spend, tokens and top models for the last N days.", "inputSchema": {"type": "object", "properties": {"days": {"type": "integer", "minimum": 1, "maximum": 90, "default": 30}}}},
    {"name": "list_blueprints", "description": "Runnable agent blueprints with their input schema and sample inputs.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "run_blueprint", "description": "Run a blueprint with a JSON input and wait for the result. Returns output, steps and cost.", "inputSchema": {"type": "object", "required": ["blueprint_id"], "properties": {"blueprint_id": {"type": "string"}, "input": {"type": "object"}}}},
    {"name": "search_knowledge", "description": "Hybrid search over a Knowledge Space the caller can see. Returns chunks with scores and sources.", "inputSchema": {"type": "object", "required": ["query"], "properties": {"space_id": {"type": "string", "description": "Omit to search every visible space"}, "query": {"type": "string"}, "k": {"type": "integer", "default": 5}}}},
]


def _ok(msg_id: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _err(msg_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _text(payload: Any) -> dict:
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=1, default=str)
    return {"content": [{"type": "text", "text": text[:20000]}], "structuredContent": payload if isinstance(payload, dict) else None, "isError": False}


def _tool_list_models(user: User, args: dict) -> Any:
    from app.governance import allowed_model_ids

    with SessionLocal() as db:
        allowed = allowed_model_ids(db, user.role)
    return {"models": [{k: m[k] for k in ("id", "name", "provider", "tier", "input_per_m", "output_per_m", "available") if k in m} for m in catalog_payload() if m["id"] in allowed]}


def _tool_usage_summary(user: User, args: dict) -> Any:
    from app.routers.usage import summary_for

    with SessionLocal() as db:
        return summary_for(db, user, int(args.get("days", 30)))


def _tool_list_blueprints(user: User, args: dict) -> Any:
    return {"blueprints": [{"id": b.id, "name": b.name, "summary": b.summary, "input_schema": b.input_schema, "samples": b.samples[:2]} for b in REGISTRY.values() if b.family != "Runtime"]}


def _tool_run_blueprint(user: User, args: dict) -> Any:
    from app.agents.runtime import start_run
    from app.catalog_store import get_entry
    from app.governance import check_budget

    blueprint_id = str(args.get("blueprint_id", ""))
    entry = get_entry(blueprint_id)
    if blueprint_id not in REGISTRY and (entry is None or not entry.get("runnable")):
        raise ValueError(f"Unknown blueprint {blueprint_id}")
    with SessionLocal() as db:
        budget = check_budget(db, user)
        if not budget.allowed:
            raise ValueError(budget.reason)
        run = Run(blueprint_id=blueprint_id, user_id=user.id, input=args.get("input") or {}, status="queued")
        db.add(run)
        db.commit()
        run_id = run.id
        start_run(run, background=False)
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        return {"run_id": run.id, "status": run.status, "output": run.output, "review": run.review, "steps": [{"node": s.get("node"), "summary": s.get("summary")} for s in (run.steps or [])], "cost_usd": run.cost_usd, "url": f"/operate/runs/{run.id}"}


def _tool_search_knowledge(user: User, args: dict) -> Any:
    from app.knowledge import search, visible_spaces

    query = str(args.get("query", "")).strip()
    if not query:
        raise ValueError("query is required")
    k = max(1, min(int(args.get("k", 5)), 20))
    with SessionLocal() as db:
        spaces = visible_spaces(db, user)
        if args.get("space_id"):
            spaces = [s for s in spaces if s.id == args["space_id"]]
            if not spaces:
                raise ValueError("Knowledge Space not found")
        hits = []
        for space in spaces:
            hits.extend({**h, "space_id": space.id, "space": space.name} for h in search(db, space, query, k=k))
        hits.sort(key=lambda h: -h["score"])
        return {"hits": hits[:k]}


HANDLERS = {"list_models": _tool_list_models, "usage_summary": _tool_usage_summary, "list_blueprints": _tool_list_blueprints, "run_blueprint": _tool_run_blueprint, "search_knowledge": _tool_search_knowledge}


def handle_message(msg: dict, user: User) -> dict:
    """Dispatch one JSON-RPC message. Notifications return an empty dict."""
    method = msg.get("method", "")
    msg_id = msg.get("id")
    params = msg.get("params") or {}
    if method == "initialize":
        return _ok(msg_id, {"protocolVersion": params.get("protocolVersion") or PROTOCOL_VERSION, "capabilities": {"tools": {"listChanged": False}}, "serverInfo": SERVER_INFO, "instructions": f"Signed in as {user.name} ({user.role}). Every call is metered to this person."})
    if method == "ping":
        return _ok(msg_id, {})
    if method.startswith("notifications/"):
        return {}
    if method == "tools/list":
        return _ok(msg_id, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name", "")
        handler = HANDLERS.get(name)
        if handler is None:
            return _err(msg_id, -32602, f"Unknown tool {name}")
        try:
            return _ok(msg_id, _text(handler(user, params.get("arguments") or {})))
        except Exception as exc:  # noqa: BLE001  tool errors are reported inside the result, per the spec
            return _ok(msg_id, {"content": [{"type": "text", "text": str(exc)[:1000]}], "isError": True})
    return _err(msg_id, -32601, f"Method not found: {method}")


def client_config(token: str) -> dict:
    """What a person pastes into Claude Desktop, Cursor or VS Code to connect."""
    return {"mcpServers": {"enterprise-ai-playground": {"url": f"{settings.self_url}/mcp", "headers": {"Authorization": f"Bearer {token}"}}}}
