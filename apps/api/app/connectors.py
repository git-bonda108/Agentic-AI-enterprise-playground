"""Connectors: MCP servers from the official registry, governed by admin approval, with a real MCP client for probes and tool calls.

Registry snapshot lives in catalog/connectors.json (seeded into the `connectors` table at startup); admins can sync incrementally.
Client speaks MCP over streamable HTTP (JSON-RPC 2.0): initialize, notifications/initialized, tools/list, tools/call.
"""

from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import API_DIR, settings
from app.models import Connector

REGISTRY_URL = "https://registry.modelcontextprotocol.io/v0.1/servers"
SNAPSHOT = API_DIR / "catalog" / "connectors.json"
PROTOCOL_VERSION = "2025-06-18"
PLAYGROUND_CONNECTOR_ID = "playground/mcp"

CATEGORIES: list[tuple[str, str]] = [
    ("Developer tools", r"github|gitlab|bitbucket|\bgit\b|code|repo|ci\b|build|debug|test|lint|ide|npm|pypi|docker|kubernetes|terraform"),
    ("Data and databases", r"postgres|mysql|sqlite|mongo|redis|database|\bsql\b|snowflake|bigquery|databricks|clickhouse|supabase|vector|analytics"),
    ("Cloud and infrastructure", r"aws|azure|gcp|google cloud|cloudflare|vercel|netlify|serverless|infra|devops|monitor|observab|grafana|datadog|sentry"),
    ("Search and web", r"search|browser|scrap|crawl|fetch|web\b|playwright|puppeteer|wikipedia|news"),
    ("Productivity and documents", r"notion|slack|jira|confluence|trello|asana|linear|calendar|email|gmail|outlook|drive|sharepoint|docs?\b|sheet|excel|pdf|note"),
    ("Finance and commerce", r"stripe|payment|invoice|bank|finance|shop|commerce|crypto|trading|stock|price"),
    ("AI and models", r"\bai\b|llm|model|agent|prompt|embedding|openai|anthropic|gemini|hugging|inference|rag|memory"),
    ("Security and identity", r"secur|auth|identity|vault|secret|password|okta|compliance"),
    ("Communication", r"chat|message|sms|whatsapp|telegram|discord|twilio|voice|call"),
]

# Well-known, enterprise-relevant publishers approved by default when present in the snapshot.
DEFAULT_APPROVED_PATTERNS = (
    r"^io\.github\.github/", r"^com\.microsoft\.", r"^com\.atlassian", r"^com\.notion", r"^com\.stripe", r"^com\.cloudflare",
    r"^io\.github\.aws", r"^com\.google", r"^io\.github\.upstash/context7", r"^com\.deepwiki", r"^io\.github\.microsoft/",
    r"^io\.github\.modelcontextprotocol/", r"^com\.slack", r"^com\.linear", r"^io\.github\.hubspot", r"^com\.sentry", r"^com\.vercel",
)


def categorize(text: str) -> str:
    low = text.lower()
    for name, pattern in CATEGORIES:
        if re.search(pattern, low):
            return name
    return "Other"


def publisher_of(name: str) -> str:
    """Reverse-DNS prefix before the slash, e.g. io.github.acme/server -> io.github.acme."""
    return name.split("/", 1)[0] if "/" in name else name


def display_title(name: str, title: str) -> str:
    """Registry titles are optional; "mcp" alone tells nobody anything, so derive one from the reverse-DNS name."""
    title = (title or "").strip()
    if len(title) >= 4 and title.lower() not in ("mcp", "server", "mcp server"):
        return title[:120]
    publisher, _, server = name.partition("/")
    labels = [p for p in publisher.split(".") if p not in ("com", "io", "org", "net", "dev", "ai", "app", "github", "gitlab")]
    words = [*labels[-2:], *(w for w in re.split(r"[-_]", server) if w and w.lower() not in ("mcp", "server"))]
    return " ".join(w[:1].upper() + w[1:] for w in words)[:120] or name


def normalize(item: dict) -> dict | None:
    """Trim a registry item to what the product needs. Returns None for entries without a name."""
    srv = item.get("server") or item
    meta = (item.get("_meta") or {}).get("io.modelcontextprotocol.registry/official") or {}
    name = srv.get("name")
    if not name:
        return None
    remotes = srv.get("remotes") or []
    packages = srv.get("packages") or []
    transport, remote_url, package = "other", "", None
    if remotes:
        transport = "remote"
        remote_url = remotes[0].get("url", "")
    elif packages:
        p = packages[0]
        transport = p.get("registryType", "other")
        package = {"registry": p.get("registryType", ""), "identifier": p.get("identifier", ""), "version": p.get("version", ""), "transport": (p.get("transport") or {}).get("type", "stdio")}
    env_vars = sorted({v.get("name") for p in packages for v in (p.get("environmentVariables") or []) if v.get("name")} | {h.get("name") for r in remotes for h in (r.get("headers") or []) if h.get("name")})
    description = (srv.get("description") or "").strip()
    return {
        "id": name,
        "title": display_title(name, srv.get("title") or ""),
        "description": description[:400],
        "version": str(srv.get("version") or ""),
        "publisher": publisher_of(name),
        "transport": transport,
        "remote_url": remote_url,
        "package": package,
        "env_vars": env_vars,
        "repo_url": ((srv.get("repository") or {}).get("url") or ""),
        "website": srv.get("websiteUrl") or "",
        "status": meta.get("status", "active"),
        "updated_at": meta.get("updatedAt") or meta.get("publishedAt") or "",
        "category": categorize(f"{name} {srv.get('title', '')} {description}"),
    }


def fetch_registry_page(cursor: str | None = None, updated_since: str | None = None, limit: int = 100) -> tuple[list[dict], str | None]:
    params: dict[str, Any] = {"version": "latest", "limit": limit}
    if cursor:
        params["cursor"] = cursor
    if updated_since:
        params["updated_since"] = updated_since
    with httpx.Client(timeout=30) as client:
        r = client.get(REGISTRY_URL, params=params)
        r.raise_for_status()
        body = r.json()
    return body.get("servers", []), (body.get("metadata") or {}).get("nextCursor")


def quality_signals(row: dict) -> int:
    score = 0
    score += 2 if row.get("remote_url") else 0
    score += 1 if row.get("repo_url") else 0
    score += 1 if row.get("website") else 0
    score += 1 if len(row.get("description", "")) >= 60 else 0
    score += 1 if row.get("title") and row["title"] != row["id"].split("/")[-1] else 0
    score += 1 if not str(row.get("version", "")).startswith("0.0") else 0
    return score


def default_approval(row: dict) -> str:
    return "approved" if any(re.search(p, row["id"]) for p in DEFAULT_APPROVED_PATTERNS) else "pending"


def playground_connector() -> dict:
    return {
        "id": PLAYGROUND_CONNECTOR_ID, "title": "Enterprise AI Playground", "description": "The playground itself as an MCP server: models, usage, blueprints, runs and knowledge search, under the caller's policy and budget.",
        "version": "1.0.0", "publisher": "playground", "transport": "remote", "remote_url": f"{settings.self_url}/mcp", "package": None, "env_vars": ["PLAYGROUND_TOKEN"],
        "repo_url": "https://github.com/git-bonda108/Agentic-AI-enterprise-playground", "website": "", "status": "active", "updated_at": datetime.now(UTC).isoformat(), "category": "AI and models",
    }


def _row_to_model(row: dict, approval: str | None = None) -> Connector:
    return Connector(
        id=row["id"], title=row["title"], description=row["description"], version=row["version"], publisher=row["publisher"], category=row["category"],
        transport=row["transport"], remote_url=row["remote_url"], package=row["package"], env_vars=row["env_vars"], repo_url=row["repo_url"], website=row["website"],
        status=row["status"], registry_updated_at=row["updated_at"], signals=quality_signals(row), approval=approval or default_approval(row),
    )


def seed_connectors(db: Session) -> int:
    """Load the committed snapshot into an empty table. Always ensures the playground's own connector exists."""
    inserted = 0
    if db.scalar(select(func.count(Connector.id))) == 0 and SNAPSHOT.exists():
        rows = json.loads(SNAPSHOT.read_text())
        db.bulk_save_objects([_row_to_model(r) for r in rows])
        inserted = len(rows)
    if db.get(Connector, PLAYGROUND_CONNECTOR_ID) is None:
        db.add(_row_to_model(playground_connector(), approval="approved"))
        inserted += 1
    db.commit()
    return inserted


def sync_registry(db: Session, max_pages: int = 200) -> dict:
    """Incremental sync from the live registry using the newest `updated_at` seen so far."""
    since = db.scalar(select(func.max(Connector.registry_updated_at)).where(Connector.id != PLAYGROUND_CONNECTOR_ID))
    cursor, pages, added, updated = None, 0, 0, 0
    while pages < max_pages:
        servers, cursor = fetch_registry_page(cursor=cursor, updated_since=since or None)
        pages += 1
        for item in servers:
            row = normalize(item)
            if row is None:
                continue
            existing = db.get(Connector, row["id"])
            if existing is None:
                db.add(_row_to_model(row))
                added += 1
            else:
                for k in ("title", "description", "version", "transport", "remote_url", "package", "env_vars", "repo_url", "website", "status", "category"):
                    setattr(existing, k, row[k])
                existing.registry_updated_at = row["updated_at"]
                existing.signals = quality_signals(row)
                updated += 1
        if not cursor or not servers:
            break
    db.commit()
    return {"pages": pages, "added": added, "updated": updated, "since": since}


def payload(c: Connector) -> dict:
    return {
        "id": c.id, "title": c.title, "description": c.description, "version": c.version, "publisher": c.publisher, "category": c.category,
        "transport": c.transport, "remote_url": c.remote_url, "package": c.package, "env_vars": c.env_vars or [], "repo_url": c.repo_url, "website": c.website,
        "status": c.status, "approval": c.approval, "approved_by": c.approved_by, "approval_note": c.approval_note, "signals": c.signals,
        "registry_updated_at": c.registry_updated_at, "install": install_snippet(c),
    }


def install_snippet(c: Connector) -> dict:
    """Configuration a client such as Claude Desktop, Cursor or VS Code would use."""
    key = c.id.split("/")[-1]
    if c.transport == "remote":
        return {key: {"url": c.remote_url, **({"headers": {v: f"${{{v}}}" for v in (c.env_vars or [])}} if c.env_vars else {})}}
    pkg = c.package or {}
    ident = pkg.get("identifier", key)
    if c.transport == "npm":
        cfg: dict = {"command": "npx", "args": ["-y", ident]}
    elif c.transport == "pypi":
        cfg = {"command": "uvx", "args": [ident]}
    elif c.transport in ("oci", "docker"):
        cfg = {"command": "docker", "args": ["run", "-i", "--rm", ident]}
    else:
        cfg = {"command": ident}
    if c.env_vars:
        cfg["env"] = {v: f"${{{v}}}" for v in c.env_vars}
    return {key: cfg}


# ---------------------------------------------------------------- MCP client ----------------------------------------------------------------

class McpError(Exception):
    pass


def _parse_response(r: httpx.Response) -> dict:
    ctype = r.headers.get("content-type", "")
    if "text/event-stream" in ctype:
        for line in r.text.replace("\r\n", "\n").split("\n"):
            if line.startswith("data:"):
                try:
                    msg = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                if isinstance(msg, dict) and ("result" in msg or "error" in msg):
                    return msg
        raise McpError("Server streamed no JSON-RPC result")
    try:
        return r.json()
    except json.JSONDecodeError as exc:
        raise McpError(f"Non-JSON response ({r.status_code})") from exc


class McpClient:
    """Minimal streamable-HTTP MCP client. Loopback calls to the playground's own server bypass the network."""

    def __init__(self, url: str, headers: dict[str, str] | None = None, timeout: float = 12.0, loopback_user=None):
        self.url = url
        self.headers = {"content-type": "application/json", "accept": "application/json, text/event-stream", **(headers or {})}
        self.timeout = timeout
        self.session_id: str | None = None
        self.loopback_user = loopback_user
        self._id = 0

    @property
    def is_loopback(self) -> bool:
        return self.url.rstrip("/") == f"{settings.self_url.rstrip('/')}/mcp"

    def _next(self) -> int:
        self._id += 1
        return self._id

    def request(self, method: str, params: dict | None = None) -> dict:
        msg = {"jsonrpc": "2.0", "id": self._next(), "method": method, "params": params or {}}
        if self.is_loopback:
            from app.mcp_server import handle_message

            if self.loopback_user is None:
                raise McpError("Authentication required (loopback needs a signed-in user)")
            resp = handle_message(msg, self.loopback_user)
        else:
            headers = dict(self.headers)
            if self.session_id:
                headers["mcp-session-id"] = self.session_id
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                r = client.post(self.url, headers=headers, content=json.dumps(msg))
            if r.status_code in (401, 403):
                raise McpError(f"Authentication required ({r.status_code})")
            if r.status_code >= 400:
                raise McpError(f"HTTP {r.status_code}: {r.text[:200]}")
            if r.headers.get("mcp-session-id"):
                self.session_id = r.headers["mcp-session-id"]
            resp = _parse_response(r)
        if "error" in resp:
            raise McpError(str(resp["error"].get("message", resp["error"]))[:300])
        return resp.get("result", {})

    def notify(self, method: str, params: dict | None = None) -> None:
        if self.is_loopback:
            return
        headers = dict(self.headers)
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        try:
            with httpx.Client(timeout=self.timeout) as client:
                client.post(self.url, headers=headers, content=json.dumps({"jsonrpc": "2.0", "method": method, "params": params or {}}))
        except httpx.HTTPError:
            pass

    def initialize(self) -> dict:
        result = self.request("initialize", {"protocolVersion": PROTOCOL_VERSION, "capabilities": {}, "clientInfo": {"name": "enterprise-ai-playground", "version": "0.7.0"}})
        self.notify("notifications/initialized")
        return result

    def list_tools(self) -> list[dict]:
        result = self.request("tools/list")
        return result.get("tools", [])

    def call_tool(self, name: str, arguments: dict) -> dict:
        return self.request("tools/call", {"name": name, "arguments": arguments})


def probe(url: str, headers: dict[str, str] | None = None, loopback_user=None) -> dict:
    """Connect, list tools, and report. Never raises: the UI shows the outcome either way."""
    started = time.perf_counter()
    client = McpClient(url, headers, loopback_user=loopback_user)
    try:
        info = client.initialize()
        tools = client.list_tools()
        return {
            "ok": True, "server": info.get("serverInfo", {}), "protocol": info.get("protocolVersion", ""), "tools": [{"name": t.get("name"), "description": (t.get("description") or "")[:240], "input_schema": t.get("inputSchema", {})} for t in tools[:60]],
            "tool_count": len(tools), "latency_ms": int((time.perf_counter() - started) * 1000), "auth_required": False, "error": None,
        }
    except McpError as exc:
        text = str(exc)
        return {"ok": False, "server": {}, "protocol": "", "tools": [], "tool_count": 0, "latency_ms": int((time.perf_counter() - started) * 1000), "auth_required": "Authentication" in text, "error": text}
    except httpx.HTTPError as exc:
        return {"ok": False, "server": {}, "protocol": "", "tools": [], "tool_count": 0, "latency_ms": int((time.perf_counter() - started) * 1000), "auth_required": False, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}


def tool_result_text(result: dict) -> str:
    parts = []
    for item in result.get("content", []) or []:
        if item.get("type") == "text":
            parts.append(item.get("text", ""))
        else:
            parts.append(json.dumps(item)[:500])
    if result.get("structuredContent") and not parts:
        parts.append(json.dumps(result["structuredContent"])[:4000])
    return "\n".join(parts)[:6000]
