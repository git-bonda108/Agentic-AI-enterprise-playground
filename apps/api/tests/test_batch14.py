"""Batch 14: the OpenAI-compatible gateway, built-in tools, platform agents, traces, and framework projects run in the sandbox."""

import json
import socket
import threading
import time

import pytest
import uvicorn

from app.config import settings
from app.main import app


@pytest.fixture(scope="module")
def live_server(client):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="off"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    previous = settings.self_url
    settings.self_url = f"http://127.0.0.1:{port}"
    yield settings.self_url
    settings.self_url = previous
    server.should_exit = True
    thread.join(timeout=5)


def _token(client, headers) -> str:
    return client.post("/v1/tokens", headers=headers, json={"name": "sdk test"}).json()["token"]


# ------------------------------------------------------------------ gateway ------------------------------------------------------------------

def test_gateway_lists_models_and_completes_with_a_personal_token(client, headers):
    token = _token(client, headers)
    bearer = {"Authorization": f"Bearer {token}"}
    models = client.get("/openai/v1/models", headers=bearer).json()
    assert models["object"] == "list" and models["data"][0]["id"] == "smart" and any(m["id"] == "gpt-5-nano" for m in models["data"])
    res = client.post("/openai/v1/chat/completions", headers={**bearer, "X-Trace-Id": "trace-sdk-1"}, json={"model": "smart", "messages": [{"role": "user", "content": "Say hello in one line."}]})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["object"] == "chat.completion" and body["choices"][0]["message"]["role"] == "assistant" and body["choices"][0]["finish_reason"] == "stop"
    assert body["usage"]["total_tokens"] == body["usage"]["prompt_tokens"] + body["usage"]["completion_tokens"]
    assert body["usage"]["playground"]["routed"] is True and body["model"] != "smart"
    pinned = client.post("/openai/v1/chat/completions", headers=bearer, json={"model": "gpt-5-nano", "messages": [{"role": "system", "content": "Be brief."}, {"role": "user", "content": [{"type": "text", "text": "hi"}]}], "max_tokens": 20}).json()
    assert pinned["model"] == "gpt-5-nano" and pinned["choices"][0]["message"]["content"]
    rows = client.get("/v1/usage/breakdown?days=1&by=feature", headers=headers).json()["rows"]
    assert any(r["key"] == "sdk" for r in rows)
    assert client.get("/openai/v1/models", headers={"Authorization": "Bearer pgk_nope"}).status_code == 401
    err = client.post("/openai/v1/chat/completions", headers=bearer, json={"model": "gpt-9", "messages": [{"role": "user", "content": "x"}]})
    assert err.status_code == 404 and err.json()["error"]["code"] == "model_not_found"


def test_gateway_streams_openai_chunks_and_returns_tool_calls(client, headers):
    bearer = {"Authorization": f"Bearer {_token(client, headers)}"}
    with client.stream("POST", "/openai/v1/chat/completions", headers=bearer, json={"model": "gpt-5-nano", "messages": [{"role": "user", "content": "stream please"}], "stream": True, "stream_options": {"include_usage": True}}) as res:
        text = "".join(res.iter_text())
    chunks = [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ") and line != "data: [DONE]"]
    assert chunks[0]["object"] == "chat.completion.chunk" and chunks[0]["choices"][0]["delta"]["role"] == "assistant"
    assert "".join(c["choices"][0]["delta"].get("content", "") for c in chunks).strip()
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop" and chunks[-1]["usage"]["total_tokens"] > 0
    assert text.rstrip().endswith("data: [DONE]")
    tools = [{"type": "function", "function": {"name": "lookup_invoice", "description": "Find an invoice", "parameters": {"type": "object", "required": ["number"], "properties": {"number": {"type": "string"}}}}}]
    res = client.post("/openai/v1/chat/completions", headers=bearer, json={"model": "gpt-5-nano", "messages": [{"role": "user", "content": "lookup invoice INV-9002"}], "tools": tools}).json()
    call = res["choices"][0]["message"]["tool_calls"][0]
    assert res["choices"][0]["finish_reason"] == "tool_calls" and call["type"] == "function" and call["function"]["name"] == "lookup_invoice" and json.loads(call["function"]["arguments"])


def test_the_openai_python_sdk_works_end_to_end_through_the_gateway(client, headers, live_server):
    """The real SDK, pointed at the playground: this is what every framework flavor does."""
    from openai import OpenAI

    sdk = OpenAI(base_url=f"{live_server}/openai/v1", api_key=_token(client, headers))
    ids = [m.id for m in sdk.models.list()]
    assert "smart" in ids
    completion = sdk.chat.completions.create(model="smart", messages=[{"role": "user", "content": "One line hello"}], extra_headers={"X-Trace-Id": "trace-openai-sdk"})
    assert completion.choices[0].message.content and completion.usage.total_tokens > 0
    parts = [c.choices[0].delta.content or "" for c in sdk.chat.completions.create(model="gpt-5-nano", messages=[{"role": "user", "content": "stream"}], stream=True)]
    assert "".join(parts).strip()
    trace = client.get("/v1/traces/sdk/trace-openai-sdk", headers=headers).json()
    assert trace["kind"] == "sdk" and trace["summary"]["calls"] >= 1 and trace["timeline"][0]["feature"] == "sdk"


# ------------------------------------------------------------------ built-in tools ------------------------------------------------------------------

def test_builtin_tools_work_and_are_safe(client, headers):
    from app.agents.tools import call_builtin, catalog, tool_specs
    from app.db import SessionLocal
    from app.models import User

    assert {t["id"] for t in catalog()} == {"current_date", "calculate", "query_dataset", "search_knowledge", "fetch_url", "run_python"}
    assert [t["function"]["name"] for t in tool_specs(["calculate", "nope", "run_python"])] == ["calculate", "run_python"]
    with SessionLocal() as db:
        user = db.get(User, "u1")
        assert call_builtin("calculate", {"expression": "round(6 * 7 / 2, 1)"}, user, db) == "round(6 * 7 / 2, 1) = 21.0"
        assert "Only arithmetic" in call_builtin("calculate", {"expression": "__import__('os').system('ls')"}, user, db)
        rows = json.loads(call_builtin("query_dataset", {"dataset": "invoices", "where": {"invoice_number": "INV-9002"}}, user, db))
        assert rows["matching"] == 1 and rows["rows"][0]["invoice_number"] == "INV-9002"
        assert "Available:" in call_builtin("query_dataset", {"dataset": "nope"}, user, db)
        assert "UTC" in call_builtin("current_date", {}, user, db)
        assert "not reachable" in call_builtin("fetch_url", {"url": "https://localhost/secret"}, user, db)
        assert "Only public https" in call_builtin("fetch_url", {"url": "http://example.com"}, user, db)
        assert call_builtin("run_python", {"code": "print(sum(range(5)))"}, user, db).strip() == "10"
        assert "Unknown built-in" in call_builtin("teleport", {}, user, db)


def test_wizard_agent_with_builtin_tools_calls_them_in_a_run(client, headers):
    agent = client.post("/v1/custom-agents", headers=headers, json={
        "name": "Calculator helper", "description": "Answers arithmetic questions with the calculate tool.",
        "instructions": "You answer arithmetic questions. Always use the calculate tool for any maths and quote its result.",
        "builtin_tools": ["calculate", "current_date"], "starters": ["calculate 6 * 7"], "published": False,
    }).json()
    assert agent["builtin_tools"] == ["calculate", "current_date"]
    entry = client.get(f"/v1/catalog/{agent['id']}", headers=headers).json()
    assert entry["builtin_tools"] == ["calculate", "current_date"]
    run = client.post("/v1/runs", headers=headers, json={"blueprint_id": agent["id"], "input": {"task": "calculate 6 * 7 please"}, "wait": True}).json()
    assert run["status"] == "completed", run
    calls = run["output"]["tool_calls"]
    assert calls and calls[0]["tool"] == "calculate" and calls[0]["connector"] == "built-in" and "= 42" in calls[0]["result"]
    assert any(s["node"] == "tools" for s in run["steps"])
    patched = client.patch(f"/v1/custom-agents/{agent['id']}", headers=headers, json={"builtin_tools": ["run_python"]}).json()
    assert patched["builtin_tools"] == ["run_python"]
    client.delete(f"/v1/custom-agents/{agent['id']}", headers=headers)


# ------------------------------------------------------------------ platform agents ------------------------------------------------------------------

@pytest.mark.parametrize("bid,expect_key", [("key-health-check", "results"), ("cost-sentinel", "anomalies"), ("connector-reviewer", "reviews"), ("onboarding-coach", "next_steps")])
def test_new_platform_agents_run_to_completion(client, headers, bid, expect_key):
    hub = client.get("/v1/blueprints", headers=headers).json()["blueprints"]
    assert any(b["id"] == bid and b["family"] == "Platform" for b in hub)
    run = client.post("/v1/runs", headers=headers, json={"blueprint_id": bid, "input": {}, "wait": True}).json()
    assert run["status"] == "completed", run.get("error")
    assert expect_key in run["output"] and len(run["steps"]) == 2
    if bid == "connector-reviewer":
        assert run["output"]["counts"]["approve"] + run["output"]["counts"]["hold"] + run["output"]["counts"]["block"] == len(run["output"]["reviews"])
    if bid == "onboarding-coach":
        assert 1 <= len(run["output"]["next_steps"]) <= 3 and all(s["href"].startswith("/") for s in run["output"]["next_steps"])


# ------------------------------------------------------------------ traces ------------------------------------------------------------------

def test_traces_list_runs_sdk_sessions_and_chats_with_timelines(client, headers):
    run = client.post("/v1/runs", headers=headers, json={"blueprint_id": "knowledge-qa", "input": {"question": "hotel limit"}, "wait": True}).json()
    conv = client.post("/v1/conversations", headers=headers, json={"title": "Trace me", "model": "gpt-5-nano"}).json()
    traces = client.get("/v1/traces?days=1", headers=headers).json()
    kinds = {t["kind"] for t in traces["traces"]}
    assert {"run", "sdk", "chat"} <= kinds and traces["scope"] == "organization"
    run_trace = next(t for t in traces["traces"] if t["kind"] == "run" and t["id"] == run["id"])
    assert run_trace["title"] == "Knowledge Q&A" and run_trace["steps"] >= 2
    detail = client.get(f"/v1/traces/run/{run['id']}", headers=headers).json()
    assert detail["summary"]["calls"] >= 1 and any(t["type"] == "step" for t in detail["timeline"]) and any(t["type"] == "call" for t in detail["timeline"])
    assert [t["at"] for t in detail["timeline"]] == sorted(t["at"] for t in detail["timeline"])
    chat = client.get(f"/v1/traces/chat/{conv['id']}", headers=headers).json()
    assert chat["title"] == "Trace me"
    assert client.get("/v1/traces/run/nope", headers=headers).status_code == 404
    explorer = {**headers, "X-User-Id": "u-trace-explorer", "X-User-Email": "trace.explorer@playground.local", "X-User-Role": "explorer"}
    assert client.get("/v1/traces?days=1", headers=explorer).json()["scope"] == "me"
    assert client.get(f"/v1/traces/run/{run['id']}", headers=explorer).status_code == 404


# ------------------------------------------------------------------ framework projects in the sandbox ------------------------------------------------------------------

@pytest.mark.parametrize("framework", ["openai-agents", "langgraph", "crewai", "agent-framework", "adk"])
def test_framework_projects_point_at_the_gateway_and_pass_their_smoke_test_in_the_sandbox(client, headers, framework):
    files = client.get(f"/v1/blueprints/sage-lens/flavor/{framework}", headers=headers).json()["files"]
    assert "PLAYGROUND_BASE_URL" in files["agent.py"] and "PLAYGROUND_TOKEN" in files["agent.py"] and "openai/v1" in files["README.md"]
    res = client.post(f"/v1/blueprints/sage-lens/flavor/{framework}/run", headers=headers, json={"mode": "smoke"}).json()
    assert res["mode"] == "smoke" and res["ok"], res["stdout"][-600:] + res["stderr"][-300:]
    assert "passed" in res["stdout"]


def test_live_framework_run_installs_and_executes_through_the_gateway(client, headers, live_server):
    """The LangGraph project really runs: pip installs into the sandbox, agent.py calls the gateway with a short-lived token."""
    pytest.importorskip("langchain_openai")  # only when the SDK is installed in this environment
    res = client.post("/v1/blueprints/knowledge-qa/flavor/langgraph/run", headers=headers, json={"mode": "live"}).json()
    assert res["ok"], res["stderr"][-800:]
    assert res["installed"] is True and res["stdout"].strip()
    tokens = client.get("/v1/tokens", headers=headers).json()["tokens"]
    assert not any(t["name"].startswith("sandbox run") for t in tokens), "the short-lived token is removed after the run"
    adk = client.post("/v1/blueprints/knowledge-qa/flavor/adk/run", headers=headers, json={"mode": "live"}).json()
    assert adk["ok"] is False and "adk run" in adk["stderr"]
