"""Two ways to build.

Every blueprint is categorised as **Gen AI** (one model call with instructions and knowledge) or **Agentic AI** (multi-step,
tools, memory, loops, human review) and carries two tracks. The code track already exists (notebook, framework flavors,
deploy scripts). This module produces the low-code track: an importable Langflow flow, an importable n8n workflow and a
Copilot Studio recipe, all generated from the blueprint manifest, plus the low-code landscape.

Format fidelity matters more than cleverness here: the Langflow flows are built from Langflow's own starter projects
(vendored, MIT) so every node carries the real component template; the n8n workflow uses the node types, versions and
parameter names of the current n8n release; the Copilot Studio recipe links only to Microsoft Learn pages that exist.
"""

from __future__ import annotations

import copy
import json
import random
import string
import uuid
from functools import lru_cache
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Connector

TEMPLATES = Path(__file__).resolve().parents[1] / "catalog" / "langflow"
GEN_AI, AGENTIC = "Gen AI", "Agentic AI"
CATEGORIES = (GEN_AI, AGENTIC)


# ------------------------------------------------------------------ categorisation ------------------------------------------------------------------

def category_for(entry: dict) -> str:
    """Gen AI: one model call with instructions and knowledge. Agentic AI: several steps, tools, review or coordination."""
    family = entry.get("family", "")
    if family in ("Topology", "Cloud"):
        return AGENTIC
    if family in ("Role", "Persona"):
        return GEN_AI
    if family == "Low-code":
        return AGENTIC if entry.get("connectors") else GEN_AI
    graph = entry.get("graph") or {}
    nodes = graph.get("nodes") or []
    kinds = [n.get("kind") for n in nodes]
    if entry.get("review_gates") or kinds.count("human") or kinds.count("tool") >= 2 or kinds.count("llm") >= 2:
        return AGENTIC
    return GEN_AI


def category_blurb(category: str) -> str:
    return "single-model patterns: chat, retrieval, extraction, classification, summarisation" if category == GEN_AI else "multi-step agents with tools, memory, checkpoints, loops and human review"


# ------------------------------------------------------------------ shared instructions ------------------------------------------------------------------

def _steps(manifest: dict) -> list[dict]:
    return list((manifest.get("graph") or {}).get("nodes") or [])


def instructions_for(manifest: dict) -> str:
    """The system prompt every studio receives: what the agent is, how it works step by step, what it must not do."""
    lines = [f"You are {manifest['name']}. {manifest.get('summary') or ''}".strip(), "", manifest.get("description", "").strip(), ""]
    steps = _steps(manifest)
    if steps:
        lines.append("Work through these steps in order and say which step you are on:")
        for i, s in enumerate(steps, 1):
            kind = s.get("kind", "llm")
            how = {"tool": "use a tool or data source; do not guess the data", "gate": "check the result against the rule and stop if it fails", "human": "pause and ask a human to decide before continuing", "llm": "reason and write"}.get(kind, "reason and write")
            lines.append(f"{i}. {s.get('label', s.get('id'))}: {how}.")
        lines.append("")
    if manifest.get("datasets"):
        lines.append("Knowledge available to you: " + ", ".join(manifest["datasets"]) + ". Cite what you used.")
    if manifest.get("review_gates"):
        lines.append("Human review: " + "; ".join(manifest["review_gates"]) + ".")
    lines += ["", "Rules: never invent numbers or citations; when data is missing, say so and stop; keep the final answer structured with a short summary first."]
    return "\n".join(lines).strip()


def playground_mcp_url() -> str:
    return f"{settings.self_url.rstrip('/')}/mcp"


# ------------------------------------------------------------------ Langflow ------------------------------------------------------------------

@lru_cache(maxsize=4)
def _template(name: str) -> dict:
    return json.loads((TEMPLATES / f"{name}.json").read_text())


def _lf_id(kind: str) -> str:
    return f"{kind}-{''.join(random.choices(string.ascii_letters + string.digits, k=5))}"


def _lf_handle(obj: dict, spaced: bool) -> str:
    """Langflow encodes handles as JSON with double quotes replaced by the œ character (its escapeJSONStringify)."""
    text = json.dumps(obj, separators=(", ", ": ") if spaced else (",", ":"))
    return text.replace('"', "œ")


def _lf_edge(source: dict, output_name: str, output_types: list[str], target: dict, field: str, input_types: list[str], field_type: str) -> dict:
    sh = {"dataType": source["data"]["type"], "id": source["id"], "name": output_name, "output_types": output_types}
    th = {"fieldName": field, "id": target["id"], "inputTypes": input_types, "type": field_type}
    return {
        "animated": False, "className": "", "selected": False,
        "id": f"reactflow__edge-{source['id']}{_lf_handle(sh, False)}-{target['id']}{_lf_handle(th, False)}",
        "source": source["id"], "sourceHandle": _lf_handle(sh, True), "target": target["id"], "targetHandle": _lf_handle(th, True),
        "data": {"sourceHandle": sh, "targetHandle": th},
    }


def _lf_node(template_flow: dict, component_type: str, position: tuple[float, float]) -> dict:
    src = next(n for n in template_flow["data"]["nodes"] if n["data"].get("type") == component_type)
    node = copy.deepcopy(src)
    node["id"] = _lf_id(component_type)
    node["data"]["id"] = node["id"]
    node["position"] = {"x": position[0], "y": position[1]}
    node["selected"] = False
    node.pop("dragging", None)
    node.pop("positionAbsolute", None)
    return node


def _lf_note(text: str, position: tuple[float, float], template_flow: dict) -> dict:
    src = next((n for n in template_flow["data"]["nodes"] if n["type"] == "noteNode"), None)
    node = copy.deepcopy(src) if src else {"type": "noteNode", "data": {"node": {"description": "", "display_name": "", "documentation": "", "template": {"backgroundColor": "indigo"}}, "type": "note"}}
    node["id"] = _lf_id("note")
    node["data"]["id"] = node["id"]
    node["data"]["type"] = "note"
    node["data"]["node"]["description"] = text
    node["data"]["node"]["template"] = {"backgroundColor": "indigo"}
    node["position"] = {"x": position[0], "y": position[1]}
    node["width"], node["height"] = 380, 300
    node["selected"] = False
    for k in ("dragging", "positionAbsolute", "resizing", "measured", "style"):
        node.pop(k, None)
    return node


def _mcp_tools_node(position: tuple[float, float]) -> dict | None:
    """The MCP Tools component, captured from a running Langflow so its template matches the installed component."""
    path = TEMPLATES / "mcp_tools.json"
    if not path.exists():
        return None
    node = json.loads(path.read_text())
    node["id"] = _lf_id(node["data"]["type"])
    node["data"]["id"] = node["id"]
    node["position"] = {"x": position[0], "y": position[1]}
    node["data"]["node"]["tool_mode"] = True  # the Agent consumes it through the Toolset output
    t = node["data"]["node"]["template"]
    token = "Bearer pgk_PASTE_YOUR_PERSONAL_TOKEN"
    # McpInput takes {name, config}; the component's own headers (a list of key/value rows) override the server config.
    t["mcp_server"]["value"] = {"name": "enterprise-ai-playground", "config": {"url": playground_mcp_url(), "headers": {"Authorization": token}}}
    t["headers"]["value"] = [{"key": "Authorization", "value": token}]
    return node


def langflow_flow(manifest: dict, category: str) -> dict:
    """An importable Langflow flow. Agentic blueprints get an Agent with the playground as MCP tools; Gen AI ones get Prompt + Language Model."""
    instructions = instructions_for(manifest)
    note_text = (
        f"## {manifest['name']} (from the Enterprise AI Playground)\n\n{manifest.get('summary', '')}\n\n"
        "**Before you run:** pick a provider and paste your API key in the model component, then create a personal token in the playground (Admin → Settings → Personal tokens) and paste it into the MCP Tools headers so the agent can call `run_blueprint`, `search_knowledge` and `list_models`.\n\n"
        "**Steps this blueprint follows:** " + " → ".join(s.get("label", s.get("id")) for s in _steps(manifest)) + "\n\n"
        "Export this flow as an MCP server from the project's MCP Server tab to use it from Claude, Cursor or n8n."
    )
    nodes: list[dict] = []
    edges: list[dict] = []
    first_input = (manifest.get("samples") or [{"input": {}}])[0]["input"]
    if category == AGENTIC:
        base = _template("simple_agent")
        chat_in = _lf_node(base, "ChatInput", (40, 320))
        agent = _lf_node(base, "Agent", (520, 200))
        chat_out = _lf_node(base, "ChatOutput", (1020, 320))
        agent["data"]["node"]["template"]["system_prompt"]["value"] = instructions
        agent["data"]["node"]["template"]["add_current_date_tool"]["value"] = True
        chat_in["data"]["node"]["template"]["input_value"]["value"] = json.dumps(first_input)
        nodes += [chat_in, agent, chat_out]
        edges.append(_lf_edge(chat_in, "message", ["Message"], agent, "input_value", ["Message"], "str"))
        edges.append(_lf_edge(agent, "response", ["Message"], chat_out, "input_value", ["Data", "JSON", "DataFrame", "Table", "Message"], "other"))
        mcp = _mcp_tools_node((40, 620))
        if mcp is not None:
            nodes.append(mcp)
            edges.append(_lf_edge(mcp, "component_as_tool", ["Tool"], agent, "tools", ["Tool"], "other"))
        nodes.append(_lf_note(note_text, (520, -160), base))
    else:
        base = _template("basic_prompting")
        chat_in = _lf_node(base, "ChatInput", (40, 320))
        prompt = _lf_node(base, "Prompt", (40, 40))
        model = _lf_node(base, "LanguageModelComponent", (520, 200))
        chat_out = _lf_node(base, "ChatOutput", (1020, 320))
        prompt["data"]["node"]["template"]["template"]["value"] = instructions
        chat_in["data"]["node"]["template"]["input_value"]["value"] = str(first_input.get("task") or first_input.get("question") or json.dumps(first_input))
        nodes += [chat_in, prompt, model, chat_out]
        edges.append(_lf_edge(chat_in, "message", ["Message"], model, "input_value", ["Message"], "str"))
        edges.append(_lf_edge(prompt, "prompt", ["Message"], model, "system_message", ["Message"], "str"))
        edges.append(_lf_edge(model, "text_output", ["Message"], chat_out, "input_value", ["Data", "JSON", "DataFrame", "Table", "Message"], "str"))
        nodes.append(_lf_note(note_text, (520, -160), base))
    return {
        "id": str(uuid.uuid4()), "name": f"{manifest['name']} (Playground)", "description": (manifest.get("summary") or manifest.get("description", ""))[:250],
        "is_component": False, "endpoint_name": None, "last_tested_version": base.get("last_tested_version", "1.10.1"), "tags": ["agents" if category == AGENTIC else "chatbots"],
        "data": {"nodes": nodes, "edges": edges, "viewport": {"x": 0, "y": 0, "zoom": 0.7}},
    }


# ------------------------------------------------------------------ n8n ------------------------------------------------------------------

def _n8n_id() -> str:
    return str(uuid.uuid4())


def _n8n_workflow_id() -> str:
    """n8n workflow ids are 16 URL-safe characters; the CLI importer requires one, the editor paste ignores it."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=16))


def n8n_workflow(manifest: dict, category: str) -> dict:
    """An importable n8n workflow (paste into the editor or `n8n import:workflow`)."""
    instructions = instructions_for(manifest)
    steps = " → ".join(s.get("label", s.get("id")) for s in _steps(manifest))
    trigger = {"parameters": {"options": {}}, "id": _n8n_id(), "name": "When chat message received", "type": "@n8n/n8n-nodes-langchain.chatTrigger", "typeVersion": 1.1, "position": [0, 300], "webhookId": _n8n_id()}
    model = {"parameters": {"model": {"__rl": True, "mode": "list", "value": "gpt-4.1-mini"}, "options": {}}, "id": _n8n_id(), "name": "OpenAI Chat Model", "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi", "typeVersion": 1.2, "position": [200, 520]}
    note = {
        "parameters": {"content": f"## {manifest['name']}\n{manifest.get('summary', '')}\n\n**Steps:** {steps}\n\n**Setup:** 1) add your model credential to the chat model node, 2) create a personal token in the playground (Admin → Settings) and add it as a Bearer credential on the *Playground MCP* tool, 3) open the chat and ask for a run.\n\nThe agent calls `run_blueprint`, `search_knowledge` and `list_models` on the playground; every call is metered to you there.", "height": 320, "width": 460, "color": 4},
        "id": _n8n_id(), "name": "About this blueprint", "type": "n8n-nodes-base.stickyNote", "typeVersion": 1, "position": [-40, -80],
    }
    if category == AGENTIC:
        agent = {"parameters": {"options": {"systemMessage": instructions}}, "id": _n8n_id(), "name": "AI Agent", "type": "@n8n/n8n-nodes-langchain.agent", "typeVersion": 2, "position": [300, 300]}
        memory = {"parameters": {"contextWindowLength": 10}, "id": _n8n_id(), "name": "Simple Memory", "type": "@n8n/n8n-nodes-langchain.memoryBufferWindow", "typeVersion": 1.3, "position": [380, 520]}
        mcp = {"parameters": {"endpointUrl": playground_mcp_url(), "serverTransport": "httpStreamable", "authentication": "bearerAuth", "include": "all"}, "id": _n8n_id(), "name": "Playground MCP", "type": "@n8n/n8n-nodes-langchain.mcpClientTool", "typeVersion": 1.2, "position": [560, 520]}
        nodes = [trigger, agent, model, memory, mcp, note]
        connections = {
            trigger["name"]: {"main": [[{"node": agent["name"], "type": "main", "index": 0}]]},
            model["name"]: {"ai_languageModel": [[{"node": agent["name"], "type": "ai_languageModel", "index": 0}]]},
            memory["name"]: {"ai_memory": [[{"node": agent["name"], "type": "ai_memory", "index": 0}]]},
            mcp["name"]: {"ai_tool": [[{"node": agent["name"], "type": "ai_tool", "index": 0}]]},
        }
        if manifest.get("review_gates"):
            wait = {
                "parameters": {"resume": "form", "formTitle": f"Review: {manifest['name']}", "formDescription": "; ".join(manifest["review_gates"]), "formFields": {"values": [
                    {"fieldLabel": "Decision", "fieldType": "dropdown", "fieldOptions": {"values": [{"option": "approve"}, {"option": "reject"}]}, "requiredField": True},
                    {"fieldLabel": "Notes", "fieldType": "textarea"},
                ]}},
                "id": _n8n_id(), "name": "Human review", "type": "n8n-nodes-base.wait", "typeVersion": 1.1, "position": [700, 300], "webhookId": _n8n_id(),
            }
            gate = {"parameters": {"conditions": {"options": {"caseSensitive": False, "leftValue": "", "typeValidation": "loose", "version": 2}, "conditions": [{"id": _n8n_id(), "leftValue": "={{ $json.Decision }}", "rightValue": "approve", "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}, "options": {}}, "id": _n8n_id(), "name": "Approved?", "type": "n8n-nodes-base.if", "typeVersion": 2.2, "position": [940, 300]}
            approved = {"parameters": {"assignments": {"assignments": [{"id": _n8n_id(), "name": "status", "value": "approved", "type": "string"}]}, "options": {}}, "id": _n8n_id(), "name": "Approved", "type": "n8n-nodes-base.set", "typeVersion": 3.4, "position": [1180, 200]}
            rejected = {"parameters": {"assignments": {"assignments": [{"id": _n8n_id(), "name": "status", "value": "rejected", "type": "string"}]}, "options": {}}, "id": _n8n_id(), "name": "Rejected", "type": "n8n-nodes-base.set", "typeVersion": 3.4, "position": [1180, 420]}
            nodes += [wait, gate, approved, rejected]
            connections[agent["name"]] = {"main": [[{"node": wait["name"], "type": "main", "index": 0}]]}
            connections[wait["name"]] = {"main": [[{"node": gate["name"], "type": "main", "index": 0}]]}
            connections[gate["name"]] = {"main": [[{"node": approved["name"], "type": "main", "index": 0}], [{"node": rejected["name"], "type": "main", "index": 0}]]}
    else:
        chain = {"parameters": {"promptType": "define", "text": "={{ $json.chatInput }}", "messages": {"messageValues": [{"message": instructions}]}}, "id": _n8n_id(), "name": "Answer", "type": "@n8n/n8n-nodes-langchain.chainLlm", "typeVersion": 1.7, "position": [300, 300]}
        nodes = [trigger, chain, model, note]
        connections = {
            trigger["name"]: {"main": [[{"node": chain["name"], "type": "main", "index": 0}]]},
            model["name"]: {"ai_languageModel": [[{"node": chain["name"], "type": "ai_languageModel", "index": 0}]]},
        }
    return {"id": _n8n_workflow_id(), "name": f"{manifest['name']} (Playground)", "nodes": nodes, "connections": connections, "settings": {"executionOrder": "v1"}, "active": False, "pinData": {}, "tags": [], "versionId": _n8n_id()}


# ------------------------------------------------------------------ Copilot Studio ------------------------------------------------------------------

MS_LEARN = "https://learn.microsoft.com/en-us/microsoft-copilot-studio/"
LEARN = {
    "start": MS_LEARN + "fundamentals-get-started",
    "trial": MS_LEARN + "requirements-licensing-subscriptions",
    "knowledge": MS_LEARN + "knowledge-copilot-studio",
    "tools": MS_LEARN + "advanced-plugin-actions",
    "orchestration": MS_LEARN + "advanced-generative-actions",
    "mcp": MS_LEARN + "agent-extend-action-mcp",
    "mcp_add": MS_LEARN + "mcp-add-existing-server-to-agent",
    "mcp_create": MS_LEARN + "mcp-create-new-server",
    "triggers": MS_LEARN + "authoring-triggers-about",
    "topics": MS_LEARN + "authoring-create-edit-topics",
    "flows": MS_LEARN + "flows-overview",
    "workflows": MS_LEARN + "workflows-experience/flows-overview",
    "classify": MS_LEARN + "workflows-experience/classify-node-workflow",
    "extract": MS_LEARN + "workflows-experience/extract-node-workflow",
    "agent_node": MS_LEARN + "workflows-experience/agent-node-workflow",
    "human_review": MS_LEARN + "workflows-experience/flows-request-for-information",
    "approvals": MS_LEARN + "flows-advanced-approvals",
    "publish": MS_LEARN + "publication-fundamentals-publish-channels",
    "credits": MS_LEARN + "requirements-messages-management",
}
KNOWLEDGE_SOURCE = {
    "invoices": "Upload the invoice files (or connect the SharePoint library where invoices land) as a file knowledge source.",
    "purchase_orders": "Connect the purchasing system: Dataverse or SQL through a connector, or an exported CSV as a file source.",
    "contracts": "A SharePoint document library of vendor contracts as a knowledge source; enable semantic search.",
    "sales": "Dataverse or SQL Server as a structured knowledge source, or the CSV as a file.",
    "policies": "The policy pages in SharePoint or the intranet as a public-website or SharePoint knowledge source.",
    "research_corpus": "Public websites (company sites, filings) as knowledge sources, limited to the domains you trust.",
    "learning_refs": "The learning catalogue (Viva Learning, an LMS export or a SharePoint list) as a knowledge source.",
    "drafts": "The drafts library in SharePoint or OneDrive as a file knowledge source.",
}
NODE_MAP = {
    "tool": ("Connector or Function", "A Power Platform connector (SharePoint, Dataverse, SQL, Excel Online, HTTP) or a Function node for deterministic logic; or an MCP tool when the system already speaks MCP", LEARN["tools"]),
    "llm": ("Agent", "An Agent node with these instructions; keep the model to reasoning and writing only", LEARN["agent_node"]),
    "gate": ("If/Else after Classify or Extract", "Classify routes by category; Extract pulls fields; If/Else applies the rule deterministically", LEARN["classify"]),
    "human": ("Human review", "The Request for information action pauses the workflow and emails the reviewer; multistage approvals for higher stakes", LEARN["human_review"]),
    "loop": ("Loop", "A Loop node over the items (invoices, drafts, questions)", LEARN["workflows"]),
}
MCP_KEYWORDS = {
    "doc-reconciliation": ["microsoft", "sharepoint", "excel", "quickbooks", "xero", "netsuite", "sap", "postgres", "neon", "zapier"],
    "sage-lens": ["sec edgar", "filings", "web search", "fetch", "news", "context7", "microsoft learn", "cloudflare"],
    "learning-path": ["notion", "google drive", "atlassian", "confluence", "youtube", "coursera", "linkedin", "microsoft learn"],
    "review-panel": ["notion", "atlassian", "confluence", "sharepoint", "google docs", "slack", "microsoft"],
    "data-analyst": ["postgres", "neon", "bigquery", "snowflake", "mysql", "google sheets", "excel", "aws"],
    "knowledge-qa": ["notion", "atlassian", "confluence", "sharepoint", "google drive", "context7", "microsoft"],
}
# Publishers whose registry entries are the vendor's own servers (io.github.* names are community projects unless listed here).
VENDOR_PUBLISHERS = {"com.notion", "com.atlassian", "com.microsoft", "io.github.microsoft", "io.github.aws", "io.github.awslabs", "com.cloudflare.mcp", "com.vercel", "com.zapier", "com.neon", "io.github.upstash", "io.github.github", "com.github", "com.stripe", "com.slack", "com.hubspot", "com.mongodb", "com.supabase", "playground"}
# Marketplaces that republish dozens of near-identical paid listings; never recommend them.
NOISY_PUBLISHERS = {"app.wishpool", "com.a2awire", "ai.trendsapi", "ai.trendsmcp", "io.github.pipeworx-io"}


def copilot_recipe(manifest: dict, category: str, connectors: list[dict]) -> dict:
    """Everything a maker needs to build this blueprint in Copilot Studio, with the exact Microsoft Learn page for each step."""
    steps = _steps(manifest)
    node_rows = []
    for s in steps:
        kind = s.get("kind", "llm")
        title, how, url = NODE_MAP.get(kind, NODE_MAP["llm"])
        node_rows.append({"step": s.get("label", s.get("id")), "kind": kind, "node": title, "how": how, "docs": url})
    knowledge = [{"dataset": d, "guidance": KNOWLEDGE_SOURCE.get(d, "Upload as a file source or connect the system of record through a connector.")} for d in manifest.get("datasets") or []]
    tools = [
        {"kind": "MCP server", "name": "Enterprise AI Playground", "why": "Lets the agent run this blueprint and search your Knowledge Spaces with the playground's governance and ledger", "how": "Add an existing MCP server with the URL below and a personal token as the API key", "url": playground_mcp_url(), "docs": LEARN["mcp_add"]},
    ]
    for c in connectors:
        tools.append({"kind": "MCP server", "name": c["title"], "why": (c.get("description") or "")[:160], "how": "Add as an MCP server (custom connector) if it is remote; otherwise host it and expose it", "url": c.get("remote_url") or c.get("repo_url") or c.get("website") or "", "docs": LEARN["mcp"]})
    tools.append({"kind": "Power Platform connector", "name": "SharePoint, Dataverse, SQL Server, Excel Online, Outlook, Teams", "why": "First-party systems of record; prefer these over MCP when the data already lives in Microsoft 365", "how": "Add a tool from a connector action; premium connectors need the standalone licence", "url": "https://learn.microsoft.com/en-us/connectors/connector-reference/connector-reference-premium-connectors", "docs": LEARN["tools"]})
    triggers = [{"name": "Manual (chat)", "when": "A person asks in Teams, Microsoft 365 Copilot or the web chat"}]
    if category == AGENTIC:
        triggers += [{"name": "Event", "when": "A new file lands in SharePoint, a form is submitted or an email arrives (agent flow trigger)"}, {"name": "Scheduled", "when": "Nightly or weekly batch runs over the queue"}]
    recipe = {
        "blueprint_id": manifest["id"], "name": manifest["name"], "category": category,
        "overview": manifest.get("summary") or manifest.get("description", ""),
        "description": (manifest.get("description") or "")[:1000],
        "instructions": instructions_for(manifest),
        "knowledge": knowledge,
        "tools": tools,
        "orchestration": "Generative orchestration must be on for tools and MCP servers to be selected automatically." if category == AGENTIC else "Classic orchestration with one topic is enough; turn on generative answers over the knowledge sources.",
        "triggers": triggers,
        "topics": [{"name": "Start", "purpose": "Collect the input the blueprint needs: " + ", ".join(f"{k} ({v})" for k, v in (manifest.get("input_schema") or {}).items())}, {"name": "Escalate", "purpose": "Hand off to a person when confidence is low or a rule fails"}],
        "workflow": node_rows,
        "review": manifest.get("review_gates") or [],
        "evaluation": "Test with the sample inputs below in the test pane, then publish to a pilot channel and watch Copilot Credits in the usage estimator.",
        "samples": manifest.get("samples") or [],
        "links": {"Get started": LEARN["start"], "Trial and licensing": LEARN["trial"], "Add knowledge": LEARN["knowledge"], "Add tools": LEARN["tools"], "Generative orchestration": LEARN["orchestration"], "Connect an MCP server": LEARN["mcp_add"], "Triggers": LEARN["triggers"], "Topics": LEARN["topics"], "Workflows": LEARN["workflows"], "Human review": LEARN["human_review"], "Approvals": LEARN["approvals"], "Publish": LEARN["publish"], "Copilot Credits": LEARN["credits"]},
    }
    recipe["markdown"] = _recipe_markdown(recipe)
    return recipe


def _recipe_markdown(r: dict) -> str:
    md = [f"# {r['name']} in Copilot Studio", "", f"*{r['category']} blueprint from the Enterprise AI Playground.*", "", "## Overview", "", r["overview"], "", "## Description (paste into the agent's description)", "", r["description"], "", "## Instructions (paste into the agent's instructions)", "", "```", r["instructions"], "```", ""]
    if r["knowledge"]:
        md += ["## Knowledge", ""] + [f"- **{k['dataset']}**: {k['guidance']}" for k in r["knowledge"]] + ["", f"Add sources: {r['links']['Add knowledge']}", ""]
    md += ["## Tools", ""] + [f"- **{t['name']}** ({t['kind']}): {t['why']}. {t['how']}." + (f" URL: `{t['url']}`" if t["url"] else "") + f" Docs: {t['docs']}" for t in r["tools"]] + ["", f"Orchestration: {r['orchestration']} ({r['links']['Generative orchestration']})", ""]
    md += ["## Triggers", ""] + [f"- **{t['name']}**: {t['when']}" for t in r["triggers"]] + ["", f"Docs: {r['links']['Triggers']}", ""]
    md += ["## Topics", ""] + [f"- **{t['name']}**: {t['purpose']}" for t in r["topics"]] + ["", f"Docs: {r['links']['Topics']}", ""]
    if r["workflow"]:
        md += ["## Workflow nodes", "", "| Blueprint step | Node | How |", "| --- | --- | --- |"] + [f"| {w['step']} | {w['node']} | {w['how']} ([docs]({w['docs']})) |" for w in r["workflow"]] + [""]
    if r["review"]:
        md += ["## Human review", ""] + [f"- {g}" for g in r["review"]] + ["", f"Docs: {r['links']['Human review']} · {r['links']['Approvals']}", ""]
    md += ["## Test and publish", "", r["evaluation"], ""] + [f"- Sample: **{s['name']}** `{json.dumps(s['input'])}`" for s in r["samples"][:3]] + ["", f"Publish: {r['links']['Publish']} · Credits: {r['links']['Copilot Credits']}", ""]
    md += ["## Next", "", f"- Get started: {r['links']['Get started']}", f"- Trial and licensing: {r['links']['Trial and licensing']}", "- Reference implementations: https://github.com/git-bonda108", ""]
    return "\n".join(md)


# ------------------------------------------------------------------ MCP recommendations ------------------------------------------------------------------

def recommend_connectors(db: Session, manifest: dict, k: int = 5) -> list[dict]:
    """The most suitable MCP servers for a blueprint.

    Candidates come from keyword matches in the registry snapshot. Admin approval and vendor-published servers are the
    enterprise signals; a keyword in the title counts more than one buried in the description; marketplaces that
    republish paid listings are excluded; near-duplicate titles collapse to one. Nothing below the bar is padded in.
    """
    from app.connectors import payload

    keywords = MCP_KEYWORDS.get(manifest["id"]) or list(manifest.get("datasets") or []) or manifest["name"].lower().split()[:3]
    scored: dict[str, tuple[float, Connector]] = {}
    for kw in keywords:
        needle = f"%{kw.lower()}%"
        stmt = select(Connector).where(func.lower(Connector.title).like(needle) | func.lower(Connector.description).like(needle) | func.lower(Connector.publisher).like(needle)).limit(40)
        for c in db.scalars(stmt).all():
            if c.approval == "blocked" or (c.publisher or "") in NOISY_PUBLISHERS or "test" in (c.title or "").lower().split("-"):
                continue
            title_hit = kw.lower() in (c.title or "").lower()
            score = (5.0 if c.approval == "approved" else 0.0) + (4.0 if (c.publisher or "") in VENDOR_PUBLISHERS else 0.0) + (3.0 if title_hit else 1.0) + (c.signals or 0) / 7.0
            if score > scored.get(c.id, (0.0, c))[0]:
                scored[c.id] = (score, c)
    ranked = sorted(scored.values(), key=lambda sc: (-sc[0], sc[1].title))
    out: list[dict] = []
    seen_titles: set[str] = set()
    for score, c in ranked:
        key = (c.title or "").lower().strip()
        if key in seen_titles or score < 4.0:
            continue
        seen_titles.add(key)
        out.append(payload(c))
        if len(out) == k:
            break
    return out


# ------------------------------------------------------------------ landscape ------------------------------------------------------------------

LANDSCAPE = [
    {"id": "copilot-studio", "name": "Microsoft Copilot Studio", "vendor": "Microsoft", "kind": "SaaS, no-code", "licence": "Standalone subscription (capacity packs, pay-as-you-go Copilot Credits) or the Teams plan in select Microsoft 365 subscriptions; free trial", "hosting": "Microsoft cloud", "mcp": "Client: connects to MCP servers (tools and resources) with generative orchestration", "best_for": "Agents for Teams and Microsoft 365 Copilot over SharePoint, Dataverse and Power Platform connectors; workflows with Classify, Extract, Agent and Human review nodes", "playground": "Recipe with instructions, knowledge, tools, triggers, topics and a workflow node map; declarative agent manifest export for custom agents", "url": "https://copilotstudio.microsoft.com", "docs": LEARN["start"], "pricing": LEARN["trial"]},
    {"id": "langflow", "name": "Langflow", "vendor": "Langflow (IBM/DataStax)", "kind": "Open source, visual builder", "licence": "MIT", "hosting": "Self-host (uv or pip, Docker), Langflow Desktop", "mcp": "Client (MCP Tools component) and server (every project is an MCP server over streamable HTTP)", "best_for": "Visual prototyping of agents and RAG with Python components you can edit; exposing flows as MCP tools", "playground": "Importable flow JSON built from Langflow's own starter components, with the playground attached as MCP tools", "url": "https://www.langflow.org/", "docs": "https://docs.langflow.org/", "pricing": "https://github.com/langflow-ai/langflow/blob/main/LICENSE"},
    {"id": "n8n", "name": "n8n", "vendor": "n8n GmbH", "kind": "Fair-code workflow automation", "licence": "Sustainable Use Licence (internal business use allowed; you may not host n8n for third parties) and n8n Enterprise Licence; n8n Cloud", "hosting": "n8n Cloud or self-host (npm, Docker, Kubernetes)", "mcp": "Client (MCP Client Tool node) and server (MCP Server Trigger)", "best_for": "Event-driven automation that mixes 400+ integrations with an AI Agent node, memory and human approvals", "playground": "Importable workflow JSON with a Chat Trigger, AI Agent, memory, the playground as an MCP Client Tool and a human-review Wait node for gated blueprints", "url": "https://n8n.io/", "docs": "https://docs.n8n.io/", "pricing": "https://n8n.io/pricing/"},
    {"id": "dify", "name": "Dify", "vendor": "LangGenius", "kind": "Open source LLM app platform", "licence": "Apache 2.0 with additional conditions (no multi-tenant service without written permission; keep front-end branding); Dify Cloud", "hosting": "Self-host (Docker Compose) or Dify Cloud", "mcp": "Client (any MCP server as a tool) and server (apps and workflows exposed as MCP servers)", "best_for": "Chatflows, workflows and RAG pipelines with a built-in dataset engine and prompt IDE", "playground": "Landscape entry and official links; use the framework flavors to port a blueprint", "url": "https://dify.ai/", "docs": "https://docs.dify.ai/", "pricing": "https://dify.ai/pricing"},
    {"id": "flowise", "name": "Flowise", "vendor": "FlowiseAI", "kind": "Open source visual builder", "licence": "Apache 2.0; Flowise Cloud", "hosting": "Self-host (npm, Docker) or Flowise Cloud", "mcp": "Client (MCP tool nodes, including custom MCP servers)", "best_for": "LangChain and LlamaIndex chatflows and multi-agent agentflows with a fast setup", "playground": "Landscape entry and official links; use the framework flavors to port a blueprint", "url": "https://flowiseai.com/", "docs": "https://docs.flowiseai.com/", "pricing": "https://flowiseai.com/pricing"},
    {"id": "power-automate", "name": "Power Automate", "vendor": "Microsoft", "kind": "SaaS workflow automation", "licence": "Per-user and per-flow plans; included in some Microsoft 365 plans", "hosting": "Microsoft cloud", "mcp": "No native MCP; pair with Copilot Studio agent flows and AI Builder", "best_for": "Deterministic business process automation across Microsoft 365, Dataverse and 1,000+ connectors; approvals", "playground": "Copilot Studio recipe maps deterministic steps to connectors and flows", "url": "https://make.powerautomate.com/", "docs": "https://learn.microsoft.com/en-us/power-automate/overview-cloud", "pricing": "https://www.microsoft.com/en-us/power-platform/products/power-automate/pricing"},
    {"id": "azure-ai-foundry", "name": "Microsoft Foundry Agent Service", "vendor": "Microsoft Azure", "kind": "Managed agent runtime", "licence": "Pay-as-you-go Azure consumption (model tokens plus agent runtime)", "hosting": "Azure", "mcp": "Client (MCP tool connects agents to remote MCP servers)", "best_for": "Production agents on Azure with identity, networking, evaluation and observability built in", "playground": "Deploy script on the Clouds page; Microsoft Agent Framework flavor", "url": "https://azure.microsoft.com/en-us/products/ai-foundry/agent-service/", "docs": "https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/model-context-protocol", "pricing": "https://azure.microsoft.com/en-us/pricing/details/ai-foundry/"},
    {"id": "vertex-agent-builder", "name": "Vertex AI Agent Builder (ADK and Agent Engine)", "vendor": "Google Cloud", "kind": "Managed agent runtime and SDK", "licence": "Pay-as-you-go Google Cloud consumption; ADK is Apache 2.0", "hosting": "Google Cloud", "mcp": "Client (ADK MCPToolset; Google-managed remote MCP servers for Google Cloud services)", "best_for": "Multi-agent systems with ADK, A2A and Gemini, deployed to Agent Engine", "playground": "Google ADK flavor and Agent Engine deploy script", "url": "https://cloud.google.com/products/agent-builder", "docs": "https://google.github.io/adk-docs/tools/mcp-tools/", "pricing": "https://cloud.google.com/vertex-ai/pricing"},
    {"id": "bedrock-agentcore", "name": "Amazon Bedrock AgentCore", "vendor": "AWS", "kind": "Managed agent runtime and gateway", "licence": "Pay-as-you-go AWS consumption", "hosting": "AWS", "mcp": "Client and server (AgentCore Gateway turns APIs and Lambda functions into MCP tools and connects to MCP servers)", "best_for": "Framework-agnostic agents at scale with identity, memory, gateway and observability", "playground": "AgentCore deploy script; Strands and LangGraph flavors", "url": "https://aws.amazon.com/bedrock/agentcore/", "docs": "https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-using-mcp.html", "pricing": "https://aws.amazon.com/bedrock/agentcore/pricing/"},
]

STUDIOS = [
    {"id": "langflow", "name": "Langflow", "artefact": "flow.json", "install": "uv pip install langflow  ·  uv run langflow run", "steps": ["Install Langflow 1.12 or later and open http://localhost:7860", "Projects → Upload the downloaded flow JSON (or drag it onto the canvas)", "In the model or Agent component choose a provider and paste your API key", "Create a personal token in the playground (Admin → Settings) and paste it in the MCP Tools headers", "Open the Playground panel and send the sample input; export the project as an MCP server when it works"], "docs": "https://docs.langflow.org/concepts-flows-import", "mcp_docs": "https://docs.langflow.org/mcp-server", "install_docs": "https://docs.langflow.org/get-started-installation"},
    {"id": "n8n", "name": "n8n", "artefact": "workflow.json", "install": "npx n8n  (or Docker: docker run -it --rm -p 5678:5678 docker.n8n.io/n8nio/n8n)", "steps": ["Start n8n and open http://localhost:5678", "Open a new workflow and paste the JSON into the canvas, or run n8n import:workflow --input=workflow.json", "Add your model credential to the chat model node", "Create a personal token in the playground and add it as a Bearer credential on the Playground MCP tool", "Open the chat panel and ask the agent to run the blueprint; gated blueprints pause at the Human review form"], "docs": "https://docs.n8n.io/workflows/export-import/", "mcp_docs": "https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.toolmcp/", "install_docs": "https://docs.n8n.io/hosting/installation/npm/"},
    {"id": "copilot", "name": "Copilot Studio", "artefact": "recipe.md", "install": "Sign in at https://copilotstudio.microsoft.com (trial available with a work account)", "steps": ["Create an agent and paste the description and instructions from the recipe", "Add the knowledge sources the recipe lists", "Add tools: the playground as an MCP server, then first-party connectors", "Turn on generative orchestration; add the triggers and topics", "Build the workflow with the node map (Classify, Extract, Agent, Human review), test with the samples, publish to a pilot channel"], "docs": LEARN["start"], "mcp_docs": LEARN["mcp_add"], "install_docs": LEARN["trial"]},
]
