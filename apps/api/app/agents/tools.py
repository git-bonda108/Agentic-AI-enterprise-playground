"""Built-in tools any agent can use without an MCP server.

Each tool is a plain function with an OpenAI-style schema. They run inside the API with the caller's identity, so knowledge
search sees only the caller's spaces and code runs in the caller's sandbox. Network access is limited to public HTTPS.
"""

from __future__ import annotations

import ast
import ipaddress
import json
import operator
import re
import socket
from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models import User

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv, ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {"round": round, "min": min, "max": max, "abs": abs, "sum": sum}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS:
        return _FUNCS[node.func.id](*[_safe_eval(a) for a in node.args])
    if isinstance(node, ast.List | ast.Tuple):
        return [_safe_eval(e) for e in node.elts]
    raise ValueError("Only arithmetic is allowed")


_EXPR_RE = re.compile(r"[0-9][0-9\s+\-*/().,%^]*[0-9)]|[0-9]")


def calculate(args: dict, user: User, db: Session) -> str:
    """Evaluates the expression; if the model wrapped it in words, the longest arithmetic run inside is used."""
    raw = str(args.get("expression", "")).strip()[:200]
    normalised = raw.replace("^", "**").replace("×", "*").replace("÷", "/")
    candidates = [normalised] + sorted((m.group(0).strip() for m in _EXPR_RE.finditer(normalised)), key=len, reverse=True)
    last_error = "empty expression"
    for expr in candidates:
        if not expr:
            continue
        try:
            value = _safe_eval(ast.parse(expr, mode="eval"))
            return f"{expr} = {value}"
        except (ValueError, SyntaxError, TypeError, ZeroDivisionError) as exc:
            last_error = str(exc)
    return f"Cannot evaluate '{raw}': {last_error}"


def current_date(args: dict, user: User, db: Session) -> str:
    now = datetime.now(UTC)
    return now.strftime("%A %d %B %Y, %H:%M UTC")


def query_dataset(args: dict, user: User, db: Session) -> str:
    from app.agents.data import DATASETS, load_csv, load_json

    name = str(args.get("dataset", ""))
    spec = next((d for d in DATASETS if d["id"] == name), None)
    if spec is None:
        return "Unknown dataset. Available: " + ", ".join(d["id"] for d in DATASETS)
    rows = load_csv(spec["file"]) if spec["file"].endswith(".csv") else load_json(spec["file"])
    if isinstance(rows, dict):
        rows = [{"key": k, "items": v} for k, v in rows.items()]
    where = args.get("where") or {}
    if isinstance(where, dict) and where:
        rows = [r for r in rows if all(str(r.get(k, "")).lower() == str(v).lower() for k, v in where.items())]
    limit = max(1, min(int(args.get("limit") or 20), 50))
    return json.dumps({"dataset": name, "matching": len(rows), "rows": rows[:limit]}, default=str)[:6000]


def search_knowledge(args: dict, user: User, db: Session) -> str:
    from app.knowledge import search, visible_spaces

    query = str(args.get("query", "")).strip()
    if not query:
        return "Give a query."
    spaces = visible_spaces(db, user)
    if args.get("space_id"):
        spaces = [s for s in spaces if s.id == args["space_id"]]
    hits: list[dict] = []
    for s in spaces[:5]:
        for h in search(db, s, query, k=int(args.get("k") or 4)):
            hits.append({"space": s.name, "title": h.get("title"), "text": (h.get("text") or "")[:400], "score": round(float(h.get("score") or 0), 3), "cite": h.get("cite")})
    hits.sort(key=lambda h: -h["score"])
    return json.dumps({"query": query, "hits": hits[:8]})[:6000] if hits else "No passages matched in your Knowledge Spaces."


def _blocked_host(host: str) -> bool:
    if host == "localhost" or host.endswith((".local", ".internal")):
        return True
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return True
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return True
    return False


def fetch_url(args: dict, user: User, db: Session) -> str:
    import httpx

    url = str(args.get("url", "")).strip()
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return "Only public https URLs can be fetched."
    if _blocked_host(parsed.hostname):
        return "That host is not reachable from the playground (private or local addresses are blocked)."
    try:
        r = httpx.get(url, timeout=15, follow_redirects=True, headers={"User-Agent": "enterprise-ai-playground/1.1"})
    except httpx.HTTPError as exc:
        return f"Fetch failed: {exc}"
    text = r.text
    if "html" in r.headers.get("content-type", ""):
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
    return f"HTTP {r.status_code} {url}\n{text[:12000]}"


def run_python(args: dict, user: User, db: Session) -> str:
    from app.notebooks import execute_local

    code = str(args.get("code", ""))[:8000]
    res = execute_local(code, {}, timeout=20, user_id=user.id)
    out = res["stdout"].strip()
    err = res["stderr"].strip()
    return (out + ("\n[stderr]\n" + err if err else "")) or f"(no output, exit {res['exit_code']})"


BUILTIN_TOOLS: dict[str, dict] = {
    "current_date": {"fn": current_date, "description": "Today's date and time in UTC.", "parameters": {"type": "object", "properties": {}}, "blurb": "Lets the agent reason about deadlines and recency."},
    "calculate": {"fn": calculate, "description": "Evaluate an arithmetic expression exactly (numbers, + - * / ** %, round, min, max, abs, sum).", "parameters": {"type": "object", "required": ["expression"], "properties": {"expression": {"type": "string"}}}, "blurb": "Deterministic arithmetic; the model never does maths in its head."},
    "query_dataset": {"fn": query_dataset, "description": "Read rows from a playground dataset, optionally filtered by exact field values.", "parameters": {"type": "object", "required": ["dataset"], "properties": {"dataset": {"type": "string", "description": "invoices, purchase_orders, contracts, sales, policies, research_corpus, learning_refs, drafts"}, "where": {"type": "object"}, "limit": {"type": "integer"}}}, "blurb": "Structured lookups in the mock data (swap for your systems later)."},
    "search_knowledge": {"fn": search_knowledge, "description": "Hybrid search across the caller's Knowledge Spaces; returns passages with citations.", "parameters": {"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "space_id": {"type": "string"}, "k": {"type": "integer"}}}, "blurb": "Grounded answers from documents you loaded."},
    "fetch_url": {"fn": fetch_url, "description": "Fetch a public https page and return its text (12,000 characters at most).", "parameters": {"type": "object", "required": ["url"], "properties": {"url": {"type": "string"}}}, "blurb": "Public web pages only; private and local addresses are blocked."},
    "run_python": {"fn": run_python, "description": "Run a short Python snippet in the caller's sandbox and return its output (20 seconds at most).", "parameters": {"type": "object", "required": ["code"], "properties": {"code": {"type": "string"}}}, "blurb": "Computation, parsing and pandas in an isolated process."},
}


def catalog() -> list[dict]:
    return [{"id": k, "description": v["description"], "blurb": v["blurb"], "parameters": v["parameters"]} for k, v in BUILTIN_TOOLS.items()]


def tool_specs(names: list[str]) -> list[dict]:
    """OpenAI-style tool specs for the selected built-ins; unknown names are ignored."""
    return [{"type": "function", "function": {"name": n, "description": BUILTIN_TOOLS[n]["description"], "parameters": BUILTIN_TOOLS[n]["parameters"]}, "builtin": True} for n in names if n in BUILTIN_TOOLS]


def call_builtin(name: str, args: dict, user: User, db: Session) -> str:
    tool = BUILTIN_TOOLS.get(name)
    if tool is None:
        return f"Unknown built-in tool {name}"
    try:
        return tool["fn"](args or {}, user, db)
    except Exception as exc:  # noqa: BLE001  (a tool failure is a result the model should see, not a crashed run)
        return f"Tool {name} failed: {exc}"
