"""Generic prompt agent: runs any catalog entry (imported role, persona, topology or low-code template) with governed models."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.blueprints.knowledge_qa import _terms
from app.agents.core import Blueprint, RunState, register, step
from app.agents.data import load_json
from app.agents.runtime import ctx_from_config
from app.catalog_store import get_entry

KNOWLEDGE_FILES = {"policies": "policies.json", "learning_refs": "learning_refs.json"}


def _retrieve(knowledge: list[str], task: str) -> list[dict]:
    q = _terms(task)
    hits: list[dict] = []
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
    return hits[:3]


def prepare(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    entry = get_entry(ctx.blueprint_id)
    if entry is None:
        raise RuntimeError(f"Catalog entry {ctx.blueprint_id} not found")
    task = str(state["input"].get("task", "")).strip() or "Describe what you do and how you approach a typical task."
    knowledge = _retrieve(entry.get("knowledge", []), task)
    data = {"entry_id": entry["id"], "name": entry["name"], "family": entry["family"], "tier": entry.get("tier", "Workhorse"), "task": task, "context": str(state["input"].get("context", "")), "knowledge": knowledge, "source": entry["source"]["url"]}
    note = f"Loaded '{entry['name']}' from {entry['source']['title']}" + (f"; retrieved {len(knowledge)} knowledge items" if entry.get("knowledge") else "")
    return {"data": data, **step(state, "prepare", note, {"knowledge": [k["id"] for k in knowledge]})}


def respond(state: RunState, config) -> dict:
    ctx = ctx_from_config(config)
    d = state["data"]
    entry = get_entry(d["entry_id"]) or {}
    system = entry.get("instructions", "")
    if entry.get("family") in ("Role", "Persona", "Topology"):
        system += "\n\nYou are running inside the Enterprise AI Playground with no filesystem or shell. Where your instructions mention tools you do not have, describe what you would do instead. Answer in markdown."
    user = d["task"]
    if d["context"]:
        user += f"\n\nContext:\n{d['context']}"
    if d["knowledge"]:
        user += "\n\nKnowledge:\n" + "\n".join(f"[{k['id']}] {k['title']}: {k['body']}" for k in d["knowledge"])
    text = ctx.llm(d["tier"], system, user, max_tokens=1800)
    return {"data": {**d, "answer": text}, **step(state, "respond", f"{d['name']} responded ({len(text)} chars)", kind="llm")}


def check(state: RunState, config) -> dict:
    d = state["data"]
    answer = d["answer"]
    problems = []
    if len(answer.strip()) < 20:
        problems.append("Answer is too short")
    if d["knowledge"] and not any(k["id"] in answer for k in d["knowledge"]):
        answer += "\n\nSources: " + ", ".join(f"[{k['id']}] {k['title']}" for k in d["knowledge"])
    output = {"answer_md": answer, "agent": d["name"], "family": d["family"], "knowledge": [k["id"] for k in d["knowledge"]], "problems": problems, "source": d["source"]}
    return {"output": output, **step(state, "check", "Output check passed" if not problems else f"Output check: {', '.join(problems)}", kind="gate")}


def build(checkpointer):
    g = StateGraph(RunState)
    g.add_node("prepare", prepare)
    g.add_node("respond", respond)
    g.add_node("check", check)
    g.add_edge(START, "prepare")
    g.add_edge("prepare", "respond")
    g.add_edge("respond", "check")
    g.add_edge("check", END)
    return g.compile(checkpointer=checkpointer)


register(Blueprint(
    id="prompt-agent", name="Prompt agent runner", family="Runtime", pattern="Instructions plus governed model",
    summary="Runs any catalog entry as a governed prompt agent.", description="Internal runner used by imported role, persona, topology and low-code entries.",
    tiers={"respond": "by entry"}, graph={"nodes": [], "edges": [], "columns": []}, samples=[], datasets=[], flavors=[], review_gates=[], dashboard=[], links={},
    build=build, batch=4,
))
