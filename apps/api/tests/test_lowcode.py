"""Batch 12: Gen AI / Agentic AI categorisation, Langflow flows, n8n workflows, Copilot Studio recipes, the landscape."""

import json
import re

import pytest

from app.lowcode import (
    AGENTIC,
    GEN_AI,
    LANDSCAPE,
    LEARN,
    STUDIOS,
    category_for,
    langflow_flow,
    n8n_workflow,
)

DOMAIN = ["doc-reconciliation", "sage-lens", "learning-path", "review-panel", "data-analyst", "knowledge-qa"]


def _decode_handle(text: str) -> dict:
    return json.loads(text.replace("œ", '"'))


def test_every_catalog_entry_has_a_category_and_the_domain_split_is_right(client, headers):
    body = client.get("/v1/catalog", headers=headers).json()
    assert body["stats"]["by_category"][GEN_AI] + body["stats"]["by_category"][AGENTIC] == body["stats"]["total"]
    assert all(e["category"] in (GEN_AI, AGENTIC) for e in body["entries"])
    by_id = {e["id"]: e["category"] for e in body["entries"]}
    assert by_id["knowledge-qa"] == GEN_AI
    for bid in ("doc-reconciliation", "sage-lens", "data-analyst", "review-panel", "learning-path"):
        assert by_id[bid] == AGENTIC, bid
    assert all(e["category"] == GEN_AI for e in body["entries"] if e["family"] in ("Role", "Persona"))
    assert all(e["category"] == AGENTIC for e in body["entries"] if e["family"] in ("Topology", "Cloud"))
    only = client.get(f"/v1/catalog?category={AGENTIC}", headers=headers).json()["entries"]
    assert only and all(e["category"] == AGENTIC for e in only)
    assert category_for({"family": "Low-code", "connectors": ["github"]}) == AGENTIC


@pytest.mark.parametrize("bid", DOMAIN)
def test_langflow_flow_is_structurally_valid(client, headers, bid):
    """Every edge joins real nodes on real fields with the same handle encoding Langflow itself writes."""
    flow = client.get(f"/v1/lowcode/{bid}/langflow", headers=headers).json()
    nodes = {n["id"]: n for n in flow["data"]["nodes"]}
    assert len(nodes) == len(flow["data"]["nodes"]), "node ids must be unique"
    types = [n["data"]["type"] for n in flow["data"]["nodes"]]
    assert "ChatInput" in types and "ChatOutput" in types and "note" in types
    assert flow["name"].endswith("(Playground)") and flow["is_component"] is False and flow["last_tested_version"]
    for e in flow["data"]["edges"]:
        assert e["source"] in nodes and e["target"] in nodes
        sh, th = _decode_handle(e["sourceHandle"]), _decode_handle(e["targetHandle"])
        assert sh == e["data"]["sourceHandle"] and th == e["data"]["targetHandle"]
        assert sh["id"] == e["source"] and th["id"] == e["target"]
        assert sh["name"] in {o["name"] for o in nodes[e["source"]]["data"]["node"]["outputs"]}, sh
        assert th["fieldName"] in nodes[e["target"]]["data"]["node"]["template"], th
        assert e["id"].startswith(f"reactflow__edge-{e['source']}")
    agent = next((n for n in flow["data"]["nodes"] if n["data"]["type"] == "Agent"), None)
    prompt = next((n for n in flow["data"]["nodes"] if n["data"]["type"] == "Prompt"), None)
    text = (agent or prompt)["data"]["node"]["template"]["system_prompt" if agent else "template"]["value"]
    assert "You are" in text and "never invent" in text
    if bid == "knowledge-qa":
        assert prompt is not None and agent is None, "Gen AI blueprints use Prompt + Language Model"
    else:
        assert agent is not None
        mcp = next((n for n in flow["data"]["nodes"] if "MCP" in n["data"]["type"]), None)
        if mcp is not None:  # captured from a running Langflow when available
            assert any(e["target"] == agent["id"] and _decode_handle(e["targetHandle"])["fieldName"] == "tools" for e in flow["data"]["edges"])


@pytest.mark.parametrize("bid", DOMAIN)
def test_n8n_workflow_is_structurally_valid(client, headers, bid):
    wf = client.get(f"/v1/lowcode/{bid}/n8n", headers=headers).json()
    names = [n["name"] for n in wf["nodes"]]
    assert len(set(names)) == len(names), "n8n node names must be unique"
    assert len({n["id"] for n in wf["nodes"]}) == len(names)
    for n in wf["nodes"]:
        assert re.match(r"^(@n8n/n8n-nodes-langchain|n8n-nodes-base)\.[A-Za-z]+$", n["type"]), n["type"]
        assert isinstance(n["typeVersion"], int | float) and len(n["position"]) == 2
    for src, outs in wf["connections"].items():
        assert src in names, src
        for kind, lanes in outs.items():
            assert kind in ("main", "ai_tool", "ai_languageModel", "ai_memory")
            for lane in lanes:
                for link in lane:
                    assert link["node"] in names and link["type"] == kind
    trigger = next(n for n in wf["nodes"] if n["type"].endswith("chatTrigger"))
    assert trigger["webhookId"]
    if bid == "knowledge-qa":
        assert any(n["type"].endswith("chainLlm") for n in wf["nodes"])
    else:
        agent = next(n for n in wf["nodes"] if n["type"].endswith(".agent"))
        assert "systemMessage" in agent["parameters"]["options"]
        feeding = {kind for src, outs in wf["connections"].items() for kind, lanes in outs.items() for lane in lanes for link in lane if link["node"] == agent["name"]}
        assert feeding == {"main", "ai_tool", "ai_languageModel", "ai_memory"}, feeding
        mcp = next(n for n in wf["nodes"] if n["type"].endswith("mcpClientTool"))
        assert mcp["parameters"]["endpointUrl"].endswith("/mcp") and mcp["parameters"]["serverTransport"] == "httpStreamable"
    if bid in ("doc-reconciliation", "review-panel"):
        assert any(n["type"] == "n8n-nodes-base.wait" and n["parameters"]["resume"] == "form" for n in wf["nodes"]), "gated blueprints pause for a human"
        assert any(n["type"] == "n8n-nodes-base.if" for n in wf["nodes"])
    assert wf["settings"] == {"executionOrder": "v1"} and wf["active"] is False


def test_copilot_recipe_covers_every_step_and_links_only_to_real_pages(client, headers):
    r = client.get("/v1/lowcode/doc-reconciliation/copilot", headers=headers).json()
    assert r["category"] == AGENTIC and r["instructions"].startswith("You are Document reconciliation")
    manifest = client.get("/v1/blueprints/doc-reconciliation", headers=headers).json()
    assert [w["step"] for w in r["workflow"]] == [n["label"] for n in manifest["graph"]["nodes"]]
    assert {w["node"] for w in r["workflow"] if w["kind"] == "human"} == {"Human review"}
    assert {k["dataset"] for k in r["knowledge"]} == set(manifest["datasets"])
    assert r["tools"][0]["kind"] == "MCP server" and r["tools"][0]["url"].endswith("/mcp")
    assert any(t["kind"] == "Power Platform connector" for t in r["tools"])
    assert len(r["triggers"]) == 3 and r["review"]
    for url in r["links"].values():
        assert url.startswith("https://learn.microsoft.com/en-us/microsoft-copilot-studio/")
    for section in ("# Document reconciliation in Copilot Studio", "## Instructions", "## Knowledge", "## Tools", "## Workflow nodes", "## Human review", "## Test and publish", "git-bonda108"):
        assert section in r["markdown"], section
    gen = client.get("/v1/lowcode/knowledge-qa/copilot", headers=headers).json()
    assert gen["category"] == GEN_AI and len(gen["triggers"]) == 1 and "Classic orchestration" in gen["orchestration"]


def test_tracks_downloads_and_landscape(client, headers):
    t = client.get("/v1/lowcode/sage-lens", headers=headers).json()
    assert t["category"] == AGENTIC and [s["id"] for s in t["lowcode"]] == ["langflow", "n8n", "copilot"] and [c["id"] for c in t["code"]] == ["notebook", "frameworks", "deploy", "evals"]
    assert isinstance(t["recommended_connectors"], list) and len(t["recommended_connectors"]) <= 5
    for studio, name in (("langflow", "sage-lens-langflow.json"), ("n8n", "sage-lens-n8n.json"), ("copilot", "sage-lens-copilot-studio.md")):
        d = client.get(f"/v1/lowcode/sage-lens/{studio}?download=1", headers=headers)
        assert d.status_code == 200 and name in d.headers["content-disposition"]
    assert client.get("/v1/lowcode/sage-lens/zapier", headers=headers).status_code == 404
    assert client.get("/v1/lowcode/nope/langflow", headers=headers).status_code == 404
    land = client.get("/v1/lowcode/landscape", headers=headers).json()
    assert [p["id"] for p in land["platforms"]] == [p["id"] for p in LANDSCAPE] and len(land["platforms"]) == 9
    for p in land["platforms"]:
        assert p["url"].startswith("https://") and p["docs"].startswith("https://") and p["licence"] and p["mcp"] and p["best_for"]
    assert land["playground_mcp_url"].endswith("/mcp") and [s["id"] for s in land["studios"]] == [s["id"] for s in STUDIOS]
    assert all(len(s["steps"]) == 5 for s in STUDIOS)
    assert all(v.startswith("https://learn.microsoft.com/") for v in LEARN.values())
    # a low-code catalog entry (prompt agent) also gets all three artefacts
    entry = client.get("/v1/catalog?family=Low-code&runnable=true&limit=1", headers=headers).json()["entries"][0]
    assert client.get(f"/v1/lowcode/{entry['id']}/n8n", headers=headers).status_code == 200
    flow = langflow_flow(client.get(f"/v1/blueprints/{entry['id']}", headers=headers).json(), GEN_AI)
    assert any(n["data"]["type"] == "Prompt" for n in flow["data"]["nodes"])
    wf = n8n_workflow({"id": "x", "name": "X", "graph": {"nodes": []}, "samples": []}, GEN_AI)
    assert wf["nodes"][1]["type"].endswith("chainLlm")
