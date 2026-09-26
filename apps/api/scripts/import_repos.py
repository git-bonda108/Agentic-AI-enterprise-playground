"""Refresh the Popular Git repos snapshot in apps/api/catalog/repos.json.

Run by hand (network and GITHUB_TOKEN required): `uv run python scripts/import_repos.py`. The output is committed, so the
API never calls GitHub at runtime. The list below is curated: what each repository is for and how it relates to the
playground is written here; stars, licence, language and last push come from GitHub at import time. Repositories that
GitHub does not know are reported and left out rather than invented.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "catalog" / "repos.json"
API = "https://api.github.com"
REFERENCE_OWNER = "git-bonda108"

# (full_name, category, blurb, relation to the playground, internal link)
CURATED: list[tuple[str, str, str, str, str]] = [
    # Agent frameworks and SDKs
    ("langchain-ai/langgraph", "Agent frameworks and SDKs", "Graph-based agent runtime with checkpoints, interrupts and streaming; the playground's own runtime.", "Runs every domain blueprint; a framework flavor", "/discover/frameworks"),
    ("openai/openai-agents-python", "Agent frameworks and SDKs", "OpenAI's agents SDK: agents, handoffs, guardrails, tracing.", "A framework flavor", "/discover/frameworks"),
    ("crewAIInc/crewAI", "Agent frameworks and SDKs", "Role-playing multi-agent crews with tasks and processes.", "A framework flavor", "/discover/frameworks"),
    ("microsoft/agent-framework", "Agent frameworks and SDKs", "Microsoft's unified agent framework (Semantic Kernel and AutoGen lineage) for .NET and Python.", "A framework flavor; Foundry deploy target", "/discover/frameworks"),
    ("google/adk-python", "Agent frameworks and SDKs", "Google's Agent Development Kit: tools, MCP, A2A, deploy to Agent Engine.", "A framework flavor; Agent Engine deploy target", "/discover/frameworks"),
    ("strands-agents/sdk-python", "Agent frameworks and SDKs", "AWS's model-driven agent SDK with MCP support and AgentCore deployment.", "A framework flavor; AgentCore deploy target", "/discover/frameworks"),
    ("anthropics/claude-agent-sdk-python", "Agent frameworks and SDKs", "Build agents on the same harness that powers Claude Code.", "The Claude flavor", "/discover/frameworks"),
    # Harnesses, skills and tiles
    ("affaan-m/everything-claude-code", "Harnesses and skills", "Agents, skills, hooks and rules that turn Claude Code into a full engineering harness.", "Source of 67 role agents and most of the skills catalog", "/discover/skills"),
    ("affaan-m/claude-swarm", "Harnesses and skills", "Multi-agent orchestration for Claude Code environments.", "Pattern reference for the Topology family", "/discover/blueprints"),
    ("affaan-m/agentshield", "Harnesses and skills", "Security scanner for agent configurations and MCP servers, as a CLI and GitHub Action.", "Recommended check before approving a connector", "/discover/connectors"),
    ("garrytan/gstack", "Harnesses and skills", "A stack of personas and workflows for building products with Claude Code.", "Source of the Persona family", "/discover/blueprints"),
    ("ruvnet/ruflo", "Harnesses and skills", "Swarm topologies and agent skills for coordinated multi-agent work.", "Source of the Topology family and part of the skills catalog", "/discover/blueprints"),
    ("obra/superpowers", "Harnesses and skills", "An agentic skills framework and development methodology for coding agents.", "Skill patterns worth borrowing", "/discover/skills"),
    ("NousResearch/hermes-agent", "Harnesses and skills", "The Hermes agent: a self-improving agent shell defaulting to Nemotron models on NVIDIA NIM.", "Runs on the NVIDIA NIM models in the catalog", "/discover/models"),
    ("Significant-Gravitas/AutoGPT", "Harnesses and skills", "The original autonomous agent project, now a platform for building and running agents.", "Historical reference for autonomy patterns", "/discover/blueprints"),
    # Visual builders
    ("langflow-ai/langflow", "Visual builders", "Open-source visual builder for agents and RAG with MCP client and server support (MIT).", "Every blueprint exports as a Langflow flow", "/discover/low-code"),
    ("n8n-io/n8n", "Visual builders", "Fair-code workflow automation with an AI Agent node and MCP nodes.", "Every blueprint exports as an n8n workflow", "/discover/low-code"),
    ("langgenius/dify", "Visual builders", "LLM app platform with chatflows, workflows, datasets and two-way MCP.", "Landscape entry", "/discover/low-code"),
    ("FlowiseAI/Flowise", "Visual builders", "Drag-and-drop LangChain and agent flows with MCP tool nodes.", "Landscape entry", "/discover/low-code"),
    # MCP
    ("modelcontextprotocol/servers", "MCP", "The reference MCP servers maintained by the protocol authors.", "Many appear in the MCP Marketplace", "/discover/connectors"),
    ("modelcontextprotocol/registry", "MCP", "The official MCP registry the marketplace snapshot is taken from.", "Source of the 7,547 marketplace entries", "/discover/connectors"),
    ("punkpeye/awesome-mcp-servers", "MCP", "A large curated list of MCP servers by category.", "External directory linked from the marketplace", "/discover/connectors"),
    ("microsoft/mcp", "MCP", "Microsoft's catalog of MCP servers for Azure, Microsoft 365 and developer tools.", "Several are approved in the marketplace", "/discover/connectors"),
    ("awslabs/mcp", "MCP", "AWS MCP servers for its services.", "Several are approved in the marketplace", "/discover/connectors"),
    ("github/github-mcp-server", "MCP", "GitHub's official MCP server.", "Marketplace entry", "/discover/connectors"),
    # Knowledge and data tooling
    ("Graphify-Labs/graphify", "Knowledge tooling", "Builds a knowledge graph of a codebase or folder and lets agents query it instead of grepping.", "The idea behind the Knowledge Space repository mapper", "/build/knowledge"),
    ("docling-project/docling", "Knowledge tooling", "Document parsing for PDF, Office and HTML into structured text for RAG.", "Candidate ingester for Knowledge Spaces", "/build/knowledge"),
    ("microsoft/graphrag", "Knowledge tooling", "Graph-based retrieval augmented generation.", "Pattern reference for graph retrieval", "/build/knowledge"),
    ("unclecode/crawl4ai", "Knowledge tooling", "LLM-friendly web crawler for research and ingestion.", "Candidate ingester for URL sources", "/build/knowledge"),
    # Evaluation and observability
    ("promptfoo/promptfoo", "Evaluation and observability", "Test and red-team prompts, agents and RAG with declarative evals.", "Complements the Evaluate page", "/evaluate/evals"),
    ("confident-ai/deepeval", "Evaluation and observability", "LLM evaluation framework with pytest-style tests and metrics.", "Complements the Evaluate page", "/evaluate/evals"),
    ("explodinggradients/ragas", "Evaluation and observability", "Evaluation metrics for retrieval augmented generation.", "Complements Knowledge Q&A evaluation", "/evaluate/evals"),
    ("langfuse/langfuse", "Evaluation and observability", "Open-source LLM observability, tracing and prompt management.", "Complements the Traces and Cost pages", "/operate/traces"),
    ("Arize-ai/phoenix", "Evaluation and observability", "Open-source tracing and evaluation for LLM applications.", "Complements the Traces page", "/operate/traces"),
]


def _get(url: str, token: str | None) -> dict | list | None:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "enterprise-ai-playground", **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        print(f"  ! {url} -> {exc.code}", file=sys.stderr)
        return None


def _row(repo: dict, category: str, blurb: str, relation: str, href: str) -> dict:
    return {
        "id": repo["full_name"].lower().replace("/", "--"), "full_name": repo["full_name"], "name": repo["name"], "category": category,
        "blurb": blurb, "relation": relation, "playground_href": href, "url": repo["html_url"], "homepage": repo.get("homepage") or "",
        "stars": int(repo.get("stargazers_count") or 0), "forks": int(repo.get("forks_count") or 0),
        "license": (repo.get("license") or {}).get("spdx_id") or (repo.get("license") or {}).get("name") or "No licence file",
        "language": repo.get("language") or "", "pushed_at": repo.get("pushed_at") or "", "topics": (repo.get("topics") or [])[:8], "archived": bool(repo.get("archived")),
    }


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    rows: list[dict] = []
    for full_name, category, blurb, relation, href in CURATED:
        repo = _get(f"{API}/repos/{full_name}", token)
        if not isinstance(repo, dict):
            print(f"  skipped {full_name}: not found", file=sys.stderr)
            continue
        rows.append(_row(repo, category, blurb, relation, href))
        print(f"  {repo['full_name']:<40} {repo.get('stargazers_count', 0):>7}★  {(repo.get('license') or {}).get('spdx_id')}")
    # Reference implementations: every public, non-fork repository of the author, newest push first.
    page = 1
    while True:
        batch = _get(f"{API}/users/{REFERENCE_OWNER}/repos?per_page=100&page={page}&sort=pushed", token)
        if not isinstance(batch, list) or not batch:
            break
        for repo in batch:
            if repo.get("fork") or repo.get("private"):
                continue
            rows.append(_row(repo, "Reference implementations", repo.get("description") or "Public repository by the playground's author.", "Built by the author; read it, rate it in the Showcase, borrow what fits", "/community/showcase"))
        page += 1
        if len(batch) < 100:
            break
    rows.sort(key=lambda r: (r["category"] != "Reference implementations", r["category"], -r["stars"]))
    OUT.write_text(json.dumps({"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "repos": rows}, indent=1, ensure_ascii=False))
    print(f"wrote {len(rows)} repositories to {OUT}")


if __name__ == "__main__":
    main()
