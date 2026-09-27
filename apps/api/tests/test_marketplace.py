"""Batch 13: MCP Marketplace client configurations, the featured shelf, and Popular Git repos."""

import json
import shlex

from app.mcp_clients import DIRECTORIES, client_configs

CLIENTS = ["claude-desktop", "claude-code", "cursor", "vscode", "copilot-studio", "langflow", "n8n"]


def test_playground_tile_gets_every_client_configuration(client, headers):
    body = client.get("/v1/connectors/playground/mcp/clients", headers=headers).json()
    assert body["connector"]["id"] == "playground/mcp"
    assert [c["client"] for c in body["clients"]] == CLIENTS
    by = {c["client"]: c for c in body["clients"]}
    desktop = json.loads(by["claude-desktop"]["snippet"])
    assert desktop["mcpServers"]["enterprise-ai-playground"]["command"] == "npx" and "mcp-remote" in desktop["mcpServers"]["enterprise-ai-playground"]["args"]
    code = shlex.split(by["claude-code"]["snippet"])
    assert code[:4] == ["claude", "mcp", "add", "--transport"] and code[4] == "http" and code[5] == "enterprise-ai-playground" and code[6].endswith("/mcp") and "--header" in code
    cursor = json.loads(by["cursor"]["snippet"])
    assert cursor["mcpServers"]["enterprise-ai-playground"]["url"].endswith("/mcp") and cursor["mcpServers"]["enterprise-ai-playground"]["headers"]["Authorization"].startswith("Bearer pgk_")
    vscode = json.loads(by["vscode"]["snippet"])
    assert vscode["servers"]["enterprise-ai-playground"]["type"] == "http"
    assert "Add an existing MCP server" in " ".join(by["copilot-studio"]["steps"]) and by["copilot-studio"]["docs"].startswith("https://learn.microsoft.com/")
    langflow = json.loads(by["langflow"]["snippet"])
    assert "url" in langflow["mcpServers"]["enterprise-ai-playground"]
    n8n = json.loads(by["n8n"]["snippet"])
    assert n8n["type"].endswith("mcpClientTool") and n8n["parameters"]["serverTransport"] == "httpStreamable" and n8n["parameters"]["authentication"] == "bearerAuth"
    for c in body["clients"]:
        assert c["docs"].startswith("https://") and len(c["steps"]) >= 2 and c["snippet"]
        assert "personal token" in " ".join(c["steps"]).lower()


def test_stdio_servers_get_commands_not_urls(client, headers):
    npm = client.get("/v1/connectors?transport=npm&limit=1", headers=headers).json()["connectors"][0]
    body = client.get(f"/v1/connectors/{npm['id']}/clients", headers=headers).json()
    by = {c["client"]: c for c in body["clients"]}
    desktop = json.loads(by["claude-desktop"]["snippet"])
    entry = next(iter(desktop["mcpServers"].values()))
    assert entry["command"] == "npx" and entry["args"][0] == "-y" and npm["package"]["identifier"] in entry["args"]
    assert by["claude-code"]["snippet"].startswith("claude mcp add ") and " -- npx -y " in by["claude-code"]["snippet"]
    assert json.loads(by["vscode"]["snippet"])["servers"][next(iter(desktop["mcpServers"]))]["type"] == "stdio"
    assert "remote MCP servers only" in by["copilot-studio"]["steps"][0]
    assert "supergateway" in by["n8n"]["steps"][0]
    pypi = client.get("/v1/connectors?transport=pypi&limit=1", headers=headers).json()["connectors"][0]
    cfg = client_configs(pypi)
    assert json.loads(cfg[0]["snippet"])["mcpServers"][pypi["id"].split("/")[-1]]["command"] == "uvx"
    assert client.get("/v1/connectors/nope/none/clients", headers=headers).status_code == 404


def test_featured_shelf_leads_with_the_playground_and_approved_servers(client, headers):
    body = client.get("/v1/connectors/featured", headers=headers).json()
    assert body["featured"][0]["id"] == "playground/mcp"
    assert all(c["approval"] == "approved" for c in body["featured"])
    assert 1 <= len(body["featured"]) <= 12
    assert [d["name"] for d in body["directories"]] == [d["name"] for d in DIRECTORIES] and all(d["url"].startswith("https://") for d in body["directories"])


def test_popular_repos_snapshot(client, headers):
    body = client.get("/v1/repos", headers=headers).json()
    assert body["total"] >= 40 and body["generated_at"] and body["stars_total"] > 1_000_000
    cats = [c["id"] for c in body["categories"]]
    assert cats[0] == "Reference implementations" and {"Agent frameworks and SDKs", "Visual builders", "MCP", "Knowledge tooling", "Evaluation and observability"} <= set(cats)
    for r in body["repos"]:
        assert r["url"].startswith("https://github.com/") and isinstance(r["stars"], int) and r["license"] and r["category"] in cats and r["playground_href"].startswith("/")
    refs = [r for r in body["repos"] if r["category"] == "Reference implementations"]
    assert refs and all(r["full_name"].startswith("git-bonda108/") for r in refs)
    assert any(r["full_name"] == "git-bonda108/agentic-invoice-processing" for r in refs)
    assert any(r["full_name"] == "langflow-ai/langflow" for r in body["repos"])
    only = client.get("/v1/repos?category=MCP", headers=headers).json()["repos"]
    assert only and all(r["category"] == "MCP" for r in only)
    assert client.get("/v1/repos?q=langgraph", headers=headers).json()["repos"]


def test_seeded_connectors_fit_their_column_lengths(client, headers):
    """PostgreSQL enforces VARCHAR limits that SQLite ignores; the registry snapshot holds descriptions and URLs longer than the columns."""
    from sqlalchemy import select

    from app.connectors import SNAPSHOT
    from app.db import SessionLocal, fit_columns
    from app.models import Connector

    limits = {c.name: c.type.length for c in Connector.__table__.columns if getattr(c.type, "length", None)}
    assert fit_columns(Connector, {"remote_url": "x" * 600})["remote_url"].endswith("…") and len(fit_columns(Connector, {"remote_url": "x" * 600})["remote_url"]) == 512
    assert fit_columns(Connector, {"title": "short"})["title"] == "short"
    with SessionLocal() as db:
        for c in db.scalars(select(Connector)).all():
            for name, limit in limits.items():
                v = getattr(c, name)
                assert v is None or len(v) <= limit, (c.id, name)
    import json
    rows = json.loads(SNAPSHOT.read_text())
    assert any(len(r.get("description") or "") > 400 or len(r.get("remote_url") or "") > 512 or len(r.get("website") or "") > 512 or len(r.get("repo_url") or "") > 512 for r in rows), "the snapshot should contain the overlong values this test guards against"
