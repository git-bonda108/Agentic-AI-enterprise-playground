"""Generic prompt agent: runs any catalog entry (imported role, persona, topology, low-code template or wizard agent) with governed models.

Batch 6 additions: retrieval from Knowledge Spaces, attached skills in the system prompt, and one tool-calling round over approved MCP connectors.
"""

from __future__ import annotations

import json

from langgraph.graph import END, START, StateGraph

from app.agents.blueprints.knowledge_qa import _terms
from app.agents.core import Blueprint, RunState, register, step
from app.agents.data import load_json
from app.agents.runtime import ctx_from_config
from app.catalog_store import get_entry
from app.connectors import McpClient, McpError, tool_result_text
from app.db import SessionLocal
from app.knowledge import search as space_search
from app.models import Connector, KnowledgeSpace, User
from app.skills import skill_prompt

KNOWLEDGE_FILES = {"policies": "policies.json", "learning_refs": "learning_refs.json"}
MAX_TOOLS = 40


def _retrieve(knowledge: list[str], task: str) -> list[dict]:
    q = _terms(task)
    hits: list[dict] = []
    space_ids = [k.split(":", 1)[1] for k in knowledge if k.startswith("space:")]
    if space_ids:
        with SessionLocal() as db:
            for sid in space_ids:
                space = db.get(KnowledgeSpace, sid)
                if space is None:
                    continue
                for h in space_search(db, space, task, k=4):
                    hits.append({"id": h["cite"], "title": h["title"], "body": h["text"][:800], "score": h["score"], "space": space.name})
    for name in knowledge:
        file = KNOWLEDGE_FILES.get(name)
        if not file:
            continue
        payload = load_json(file)
        docs = payload if isinstance(payload, list) else [{"id": k, "title": k, "body": " ".join(t for t, _ in v)} for k, v in payload.items()]
        for d in docs:
            body = d.get("body") or " ".join(str(v) for v in d.values())
            score = len(q & _terms(str(d.get("title", "")) + " " + body))
            if score:
                hits.append({"id": d.get("id", d.get("title")), "title": d.get("title", ""), "body": body[:800], "score": score})
    hits.sort(key=lambda h: -h["score"])
    return hits[:5]


def _tools_for(connector_ids: list[str], user: User | None) -> tuple[list[dict], list[dict]]:
    """Approved remote connectors become model tools. Returns (tool specs, connector rows)."""
    if not connector_ids:
        return [], []
    specs, rows = [], []
    with SessionLocal() as db:
        for cid in connector_ids:
            c = db.get(Connector, cid)
            if c is None or c.approval != "approved" or c.transport != "remote":
                continue
            rows.append({"id": c.id, "title": c.title, "url": c.remote_url})
            try:
                client = McpClient(c.remote_url, loopback_user=user)
                client.initialize()
                for t in client.list_tools()[:MAX_TOOLS]:
                    specs.append({"type": "function", "function": {"name": f"{t['name']}", "description": (t.get("description") or "")[:300], "parameters": t.get("inputSchema") or {"type": "object", "properties": {}}}, "connector": c.id})
            except McpError:
                continue
    return specs[:MAX_TOOLS], rows


def prepare(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    entry = get_entry(ctx.blueprint_id)
    if entry is None:
        raise RuntimeError(f"Catalog entry {ctx.blueprint_id} not found")
    task = str(state["input"].get("task", "")).strip() or "Describe what you do and how you approach a typical task."
    knowledge = _retrieve(entry.get("knowledge", []), task)
    with SessionLocal() as db:
        user = db.get(User, ctx.user_id)
    tools, connectors = _tools_for(entry.get("connectors", []), user)
    data = {
        "entry_id": entry["id"], "name": entry["name"], "family": entry["family"], "tier": entry.get("tier", "Workhorse"), "task": task, "context": str(state["input"].get("context", "")),
        "knowledge": knowledge, "source": entry["source"]["url"], "skills": entry.get("skills", []), "tools": tools, "connectors": connectors,
    }
    parts = [f"Loaded '{entry['name']}' from {entry['source']['title']}"]
    if entry.get("knowledge"):
        parts.append(f"retrieved {len(knowledge)} knowledge items")
    if data["skills"]:
        parts.append(f"{len(data['skills'])} skills attached")
    if tools:
        parts.append(f"{len(tools)} tools from {len(connectors)} connectors")
    return {"data": data, **step(state, "prepare", "; ".join(parts), {"knowledge": [k["id"] for k in knowledge], "skills": data["skills"], "tools": [t["function"]["name"] for t in tools]})}


def _system_for(entry: dict, d: dict) -> str:
    system = entry.get("instructions", "")
    if entry.get("family") in ("Role", "Persona", "Topology"):
        system += "\n\nYou are running inside the Enterprise AI Playground with no filesystem or shell. Where your instructions mention tools you do not have, describe what you would do instead. Answer in markdown."
    skills = skill_prompt(d.get("skills", []))
    if skills:
        system += "\n\nApply the following skills where relevant.\n\n" + skills
    return system


def _user_for(d: dict) -> str:
    user = d["task"]
    if d["context"]:
        user += f"\n\nContext:\n{d['context']}"
    if d["knowledge"]:
        user += "\n\nKnowledge:\n" + "\n".join(f"[{k['id']}] {k['title']}: {k['body']}" for k in d["knowledge"])
    return user


def respond(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    d = state["data"]
    entry = get_entry(d["entry_id"]) or {}
    system, user = _system_for(entry, d), _user_for(d)
    if d.get("tools"):
        specs = [{"type": t["type"], "function": t["function"]} for t in d["tools"]]
        text, calls = ctx.llm_tools(d["tier"], system + "\n\nYou may call the provided tools when they help. Use their results in your answer.", user, specs)
        if calls:
            return {"data": {**d, "pending_calls": calls, "draft": text}, **step(state, "respond", f"{d['name']} requested {len(calls)} tool call(s)", {"calls": [c["name"] for c in calls]}, kind="llm")}
        return {"data": {**d, "answer": text, "pending_calls": []}, **step(state, "respond", f"{d['name']} responded ({len(text)} chars)", kind="llm")}
    text = ctx.llm(d["tier"], system, user, max_tokens=1800)
    return {"data": {**d, "answer": text, "pending_calls": []}, **step(state, "respond", f"{d['name']} responded ({len(text)} chars)", kind="llm")}


def tools_node(state: RunState, config) -> dict:
    """Execute the requested MCP tool calls, then let the model finish with the results in hand."""
    ctx = ctx_from_config(config)
    d = state["data"]
    by_name = {t["function"]["name"]: t["connector"] for t in d["tools"]}
    with SessionLocal() as db:
        user = db.get(User, ctx.user_id)
        urls = {c["id"]: c["url"] for c in d["connectors"]}
    results = []
    for call in d.get("pending_calls", []):
        cid = by_name.get(call["name"])
        try:
            client = McpClient(urls[cid], loopback_user=user)
            client.initialize()
            res = client.call_tool(call["name"], call.get("arguments") or {})
            results.append({"tool": call["name"], "connector": cid, "arguments": call.get("arguments") or {}, "result": tool_result_text(res)[:3000], "is_error": bool(res.get("isError"))})
        except (McpError, KeyError) as exc:
            results.append({"tool": call["name"], "connector": cid, "arguments": call.get("arguments") or {}, "result": f"Tool failed: {exc}", "is_error": True})
    entry = get_entry(d["entry_id"]) or {}
    followup = _user_for(d) + "\n\nTool results:\n" + "\n\n".join(f"### {r['tool']} ({r['connector']})\nArguments: {json.dumps(r['arguments'])}\n{r['result']}" for r in results)
    text = ctx.llm(d["tier"], _system_for(entry, d) + "\n\nAnswer the request using the tool results below. Quote concrete values from them.", followup, max_tokens=1800)
    return {"data": {**d, "answer": text, "tool_results": results}, **step(state, "tools", f"Ran {len(results)} tool call(s): " + ", ".join(r["tool"] for r in results), {"results": results}, kind="tool")}


def check(state: RunState, config) -> dict:
    d = state["data"]
    answer = d.get("answer", "")
    problems = []
    if len(answer.strip()) < 20:
        problems.append("Answer is too short")
    if d["knowledge"] and not any(k["id"] in answer for k in d["knowledge"]):
        answer += "\n\nSources: " + ", ".join(f"[{k['id']}] {k['title']}" for k in d["knowledge"])
    output = {"answer_md": answer, "agent": d["name"], "family": d["family"], "knowledge": [k["id"] for k in d["knowledge"]], "knowledge_items": [{"id": k["id"], "title": k["title"], "body": k["body"][:700]} for k in d["knowledge"]], "skills": d.get("skills", []), "tool_calls": d.get("tool_results", []), "problems": problems, "source": d["source"]}
    return {"output": output, **step(state, "check", "Output check passed" if not problems else f"Output check: {', '.join(problems)}", kind="gate")}


def _after_respond(state: RunState) -> str:
    return "tools" if state["data"].get("pending_calls") else "check"


def build(checkpointer):
    g = StateGraph(RunState)
    g.add_node("prepare", prepare)
    g.add_node("respond", respond)
    g.add_node("tools", tools_node)
    g.add_node("check", check)
    g.add_edge(START, "prepare")
    g.add_edge("prepare", "respond")
    g.add_conditional_edges("respond", _after_respond, {"tools": "tools", "check": "check"})
    g.add_edge("tools", "check")
    g.add_edge("check", END)
    return g.compile(checkpointer=checkpointer)


register(Blueprint(
    id="prompt-agent", name="Prompt agent runner", family="Runtime", pattern="Instructions, knowledge, skills, tools, governed model",
    summary="Runs any catalog entry as a governed prompt agent.", description="Internal runner used by imported role, persona, topology, low-code and wizard entries.",
    tiers={"respond": "by entry"}, graph={"nodes": [], "edges": [], "columns": []}, samples=[], datasets=[], flavors=[], review_gates=[], dashboard=[], links={},
    build=build, batch=4,
))
