"""Batch 6: connectors from the MCP registry, the playground as an MCP server, Knowledge Spaces, the repository mapper, skills."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from app.config import API_DIR


def _rpc(client, headers, method, params=None, msg_id=1):
    r = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}})
    assert r.status_code == 200, r.text
    return r.json()


# ---------------------------------------------------------------- connectors ----------------------------------------------------------------

def test_connectors_seeded_and_searchable(client, headers):
    stats = client.get("/v1/connectors/stats", headers=headers).json()
    assert stats["total"] >= 1000 and "approved" in stats["by_approval"]
    body = client.get("/v1/connectors?q=playground", headers=headers).json()
    ids = [c["id"] for c in body["connectors"]]
    assert "playground/mcp" in ids
    me = client.get("/v1/connectors/playground/mcp", headers=headers).json()
    assert me["approval"] == "approved" and me["transport"] == "remote"
    assert next(iter(me["install"].values()))["url"].endswith("/mcp")
    github = client.get("/v1/connectors?q=github-mcp-server", headers=headers).json()["connectors"]
    assert github and github[0]["approval"] == "approved"


def test_probe_lists_the_playgrounds_own_tools(client, headers):
    r = client.post("/v1/connectors/playground/mcp/probe", headers=headers, json={})
    assert r.status_code == 200
    probe = r.json()
    assert probe["ok"] is True and probe["server"]["name"] == "enterprise-ai-playground"
    assert {"list_models", "run_blueprint", "search_knowledge"} <= {t["name"] for t in probe["tools"]}


def test_approval_requires_admin(client, headers):
    builder = {**headers, "X-User-Id": "u9", "X-User-Email": "ravi@playground.local", "X-User-Role": "builder"}
    assert client.post("/v1/connectors/playground/mcp/approval", headers=builder, json={"approval": "blocked"}).status_code == 403
    r = client.post("/v1/connectors/playground/mcp/approval", headers=headers, json={"approval": "approved", "note": "first-party"})
    assert r.status_code == 200 and r.json()["approval_note"] == "first-party" and r.json()["approved_by"] == "u1"


def test_call_a_connector_tool_directly(client, headers):
    r = client.post("/v1/connectors/playground/mcp/call", headers=headers, json={"tool": "list_models", "arguments": {}})
    assert r.status_code == 200, r.text
    assert "claude-sonnet-5" in r.json()["text"] and r.json()["is_error"] is False


# ---------------------------------------------------------------- MCP server and tokens ----------------------------------------------------------------

def test_mcp_endpoint_with_identity_headers(client, headers):
    init = _rpc(client, headers, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}})
    assert init["result"]["serverInfo"]["name"] == "enterprise-ai-playground"
    tools = _rpc(client, headers, "tools/list")["result"]["tools"]
    assert len(tools) == 5
    called = _rpc(client, headers, "tools/call", {"name": "list_blueprints", "arguments": {}})["result"]
    assert called["isError"] is False and "doc-reconciliation" in called["content"][0]["text"]
    unknown = _rpc(client, headers, "tools/call", {"name": "nope", "arguments": {}})
    assert unknown["error"]["code"] == -32602
    notif = client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert notif.status_code == 202


def test_personal_token_authenticates_mcp_and_meters_the_owner(client, headers):
    created = client.post("/v1/tokens", headers=headers, json={"name": "Claude Desktop"}).json()
    token = created["token"]
    assert token.startswith("pgk_") and created["client_config"]["mcpServers"]["enterprise-ai-playground"]["headers"]["Authorization"] == f"Bearer {token}"
    listing = client.get("/v1/tokens", headers=headers).json()["tokens"]
    assert any(t["id"] == created["id"] for t in listing) and all("token" not in t for t in listing)
    bearer = {"Authorization": f"Bearer {token}"}
    run = _rpc(client, bearer, "tools/call", {"name": "run_blueprint", "arguments": {"blueprint_id": "knowledge-qa", "input": {"question": "What is the hotel limit per night?"}}})["result"]
    assert run["isError"] is False and run["structuredContent"]["status"] == "completed"
    run_id = run["structuredContent"]["run_id"]
    assert client.get(f"/v1/runs/{run_id}", headers=headers).json()["user_id"] == "u1"
    assert client.post("/mcp", headers={"Authorization": "Bearer pgk_wrong"}, json={"jsonrpc": "2.0", "id": 1, "method": "ping"}).status_code == 401
    assert client.delete(f"/v1/tokens/{created['id']}", headers=headers).status_code == 204
    assert client.post("/mcp", headers=bearer, json={"jsonrpc": "2.0", "id": 1, "method": "ping"}).status_code == 401


# ---------------------------------------------------------------- knowledge spaces ----------------------------------------------------------------

def test_knowledge_space_ingest_search_and_ask(client, headers):
    models = client.get("/v1/knowledge/embedding-models", headers=headers).json()["models"]
    assert any(m["id"] == "local-hash" and m["available"] for m in models)
    space = client.post("/v1/knowledge/spaces", headers=headers, json={"name": "Travel desk", "description": "Travel rules", "visibility": "org"}).json()
    sid = space["id"]
    text = "Hotel stays are reimbursed up to 220 USD per night in major cities and 150 USD elsewhere.\n\nTaxi rides are reimbursed with a receipt. Ride sharing is allowed for business travel.\n\nBusiness class flights require director approval when the flight is longer than 8 hours."
    doc = client.post(f"/v1/knowledge/spaces/{sid}/documents/text", headers=headers, json={"title": "Travel policy", "text": text}).json()
    assert doc["chunk_count"] >= 1
    hits = client.post(f"/v1/knowledge/spaces/{sid}/search", headers=headers, json={"query": "hotel per night limit", "k": 3}).json()["hits"]
    assert hits and "220 USD" in hits[0]["text"] and hits[0]["cite"].startswith("Travel policy#")
    # embeddings were metered on the ledger as feature "knowledge"
    summary = client.get("/v1/usage/summary?days=1", headers=headers).json()
    assert "knowledge" in json.dumps(summary)
    ask = client.post(f"/v1/knowledge/spaces/{sid}/ask", headers=headers, json={"question": "What is the hotel limit per night?"}).json()
    assert ask["status"] == "completed" and ask["blueprint_id"] == "knowledge-qa"
    assert ask["output"]["grounded"] is True and ask["output"]["citations"]
    assert "Knowledge Space 'Travel desk'" in ask["steps"][0]["summary"]
    # a dataset becomes one chunk per record with the record id in the citation
    ds = client.post(f"/v1/knowledge/spaces/{sid}/documents/dataset", headers=headers, json={"dataset": "policies"}).json()
    assert ds["chunk_count"] == 10
    hits = client.post(f"/v1/knowledge/spaces/{sid}/search", headers=headers, json={"query": "purchase over 50,000 USD tender", "k": 2}).json()["hits"]
    assert hits[0]["meta"].get("record_id") == "POL-002"
    detail = client.get(f"/v1/knowledge/spaces/{sid}", headers=headers).json()
    assert detail["doc_count"] == 2 and detail["chunk_count"] >= 11 and detail["can_edit"] is True
    assert client.delete(f"/v1/knowledge/spaces/{sid}/documents/{ds['id']}", headers=headers).status_code == 204
    assert client.get(f"/v1/knowledge/spaces/{sid}", headers=headers).json()["doc_count"] == 1


def test_knowledge_visibility_rules(client, headers):
    private = client.post("/v1/knowledge/spaces", headers=headers, json={"name": "Mine only", "visibility": "private"}).json()
    other = {**headers, "X-User-Id": "u9", "X-User-Email": "ravi@playground.local", "X-User-Role": "builder", "X-User-Department": "Finance"}
    assert client.get(f"/v1/knowledge/spaces/{private['id']}", headers=other).status_code == 404
    dept = client.post("/v1/knowledge/spaces", headers=other, json={"name": "Finance desk", "visibility": "department"}).json()
    same_dept = {**other, "X-User-Id": "u8", "X-User-Email": "mei@playground.local"}
    assert client.get(f"/v1/knowledge/spaces/{dept['id']}", headers=same_dept).status_code == 200
    assert client.post(f"/v1/knowledge/spaces/{dept['id']}/documents/text", headers=same_dept, json={"title": "x", "text": "y z"}).status_code == 403
    assert client.delete(f"/v1/knowledge/spaces/{dept['id']}", headers=headers).status_code == 204  # admin may delete


def test_file_upload_extracts_text(client, headers):
    space = client.post("/v1/knowledge/spaces", headers=headers, json={"name": "Uploads"}).json()
    content = base64.b64encode(b"# Onboarding\n\nNew vendors must supply a tax certificate and a bank confirmation letter.").decode()
    doc = client.post(f"/v1/knowledge/spaces/{space['id']}/documents/file", headers=headers, json={"filename": "onboarding.md", "content_base64": content}).json()
    assert doc["source_type"] == "file" and doc["chunk_count"] == 1
    bad = client.post(f"/v1/knowledge/spaces/{space['id']}/documents/file", headers=headers, json={"filename": "empty.txt", "content_base64": base64.b64encode(b"   ").decode()})
    assert bad.status_code == 400


def test_repository_mapper_builds_a_graph_and_chunks(client, headers):
    space = client.post("/v1/knowledge/spaces", headers=headers, json={"name": "Code map"}).json()
    source = str(Path(API_DIR) / "app" / "agents")
    r = client.post(f"/v1/knowledge/spaces/{space['id']}/documents/repo", headers=headers, json={"source": source})
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["has_graph"] and doc["summary"]["files"] >= 8 and doc["summary"]["symbols"] >= 20 and doc["summary"]["edges"] >= 20
    graph = client.get(f"/v1/knowledge/spaces/{space['id']}/graph", headers=headers).json()
    kinds = {n["kind"] for n in graph["nodes"]}
    assert {"file", "function", "folder"} <= kinds and len(graph["edges"]) == doc["summary"]["edges"]
    assert any(e["kind"] == "imports" for e in graph["edges"])
    hits = client.post(f"/v1/knowledge/spaces/{space['id']}/search", headers=headers, json={"query": "start a run on a background thread", "k": 3}).json()["hits"]
    assert hits and hits[0]["meta"].get("file", "").endswith(".py")
    forbidden = client.post(f"/v1/knowledge/spaces/{space['id']}/documents/repo", headers=headers, json={"source": "/etc"})
    assert forbidden.status_code == 403


# ---------------------------------------------------------------- skills ----------------------------------------------------------------

def test_skills_catalog_search_and_detail(client, headers):
    body = client.get("/v1/skills", headers=headers).json()
    assert body["stats"]["total"] >= 300 and body["stats"]["by_source"]["everything-claude-code"] >= 250
    found = client.get("/v1/skills?q=tdd", headers=headers).json()["skills"]
    assert found and all("body" not in s for s in found) and found[0]["preview"]
    detail = client.get(f"/v1/skills/{found[0]['id']}", headers=headers).json()
    assert detail["body"] and detail["source"]["license"] == "MIT" and detail["source"]["url"].startswith("https://github.com/")
    assert client.get("/v1/skills/nope", headers=headers).status_code == 404


def test_wizard_agent_uses_skills_knowledge_space_and_connector_tools(client, headers):
    space = client.post("/v1/knowledge/spaces", headers=headers, json={"name": "Expense rules", "visibility": "org"}).json()
    client.post(f"/v1/knowledge/spaces/{space['id']}/documents/text", headers=headers, json={"title": "Expense rules", "text": "Meals are reimbursed up to 60 USD per day with receipts. Alcohol is never reimbursed."})
    skill = client.get("/v1/skills?q=tdd", headers=headers).json()["skills"][0]["id"]
    body = {"name": "Model concierge", "description": "Lists the models you may use and answers expense questions.", "instructions": "You help colleagues pick models and understand expense rules. When asked about models, list them.", "knowledge": [f"space:{space['id']}"], "tools": ["playground/mcp"], "skills": [skill], "starters": ["List the models I can use"], "published": True}
    created = client.post("/v1/custom-agents", headers=headers, json=body).json()
    assert created["skills"] == [skill] and created["tools"] == ["playground/mcp"]
    run = client.post("/v1/runs", headers=headers, json={"blueprint_id": created["id"], "input": {"task": "List the models I can use for meals questions"}, "wait": True}).json()
    assert run["status"] == "completed", run.get("error")
    nodes = [s["node"] for s in run["steps"]]
    assert nodes == ["prepare", "respond", "tools", "check"], nodes
    tool_step = next(s for s in run["steps"] if s["node"] == "tools")
    assert tool_step["detail"]["results"][0]["tool"] == "list_models" and "claude-sonnet-5" in tool_step["detail"]["results"][0]["result"]
    assert run["output"]["skills"] == [skill] and run["output"]["tool_calls"][0]["is_error"] is False
    assert any("Expense rules#" in k for k in run["output"]["knowledge"])
    # the generated project carries the skill and the MCP configuration
    files = client.get(f"/v1/blueprints/{created['id']}/flavor/langgraph", headers=headers).json()["files"]
    assert f"skills/{skill}/SKILL.md" in files and "mcp.json" in files and "/mcp" in files["mcp.json"]
    manifest = client.get(f"/v1/custom-agents/{created['id']}/export/declarative-agent", headers=headers).json()
    assert "Skill:" in manifest["instructions"]
    assert client.delete(f"/v1/custom-agents/{created['id']}", headers=headers).status_code == 204  # leave the catalog as other tests expect it
