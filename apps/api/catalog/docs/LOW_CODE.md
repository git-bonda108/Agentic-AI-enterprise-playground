# Two ways to build

Every blueprint in the playground is categorised and carries two tracks. This guide explains the categories, what each low-code studio receives, how the artefacts are generated, and where the code track lives.

## Gen AI and Agentic AI

| Category | Definition | Rule in `apps/api/app/lowcode.py` | Examples |
| --- | --- | --- | --- |
| Gen AI | One model call with instructions and knowledge | Role and Persona entries; Domain blueprints with at most one tool step and one model step and no review gate; custom agents without connectors | Knowledge Q&A, the ECC role agents, gstack personas |
| Agentic AI | Several steps with tools, memory, review or coordination | Topology and Cloud entries; Domain blueprints with a human gate, two or more tool steps or two or more model steps; custom agents with connectors | Document reconciliation, Sage Lens, Data analyst, the ruflo topologies |

The Blueprints page filters by category and every card shows its badge. The detail dialog offers **Build it your way** with both tracks.

## The low-code track

Discover → Low-code studios generates three artefacts for any runnable domain blueprint or low-code template.

### Langflow flow

An importable flow JSON built from Langflow's own starter projects (vendored under `apps/api/catalog/langflow/`, MIT), so every node carries the real component template of the Langflow release it was tested on. Agentic blueprints get Chat Input → Agent → Chat Output with the playground attached as MCP tools; Gen AI blueprints get Chat Input → Prompt → Language Model → Chat Output. The instructions are the blueprint's description, its step plan and its rules. Import it from Projects → Upload, set the model and API key, paste a personal token into the MCP Tools headers, and run. Langflow projects can then be exported as MCP servers for Claude, Cursor or n8n.

### n8n workflow

An importable workflow JSON using the current n8n node types and versions: a Chat Trigger, an AI Agent (system message = the instructions), a chat model, Simple Memory and the playground as an MCP Client Tool over streamable HTTP with bearer authentication. Blueprints with review gates get a Wait node (resume on form submission with an approve or reject decision) and an If node. Gen AI blueprints get a Basic LLM Chain instead of the agent. Paste the JSON into the editor or run `n8n import:workflow`.

### Copilot Studio recipe

Copilot Studio does not import agents from JSON, so the playground generates a recipe: overview, description, instructions, knowledge sources (mapped from the blueprint's datasets to SharePoint, Dataverse, SQL or file sources), tools (the playground as an MCP server, the most suitable MCP servers from the registry, first-party Power Platform connectors), orchestration setting, triggers, topics, a workflow node map (blueprint step → Classify, Extract, Agent, Human review, Connector or Function, If/Else, Loop), review gates, test samples and publishing. Every step links to the Microsoft Learn page that documents it; the links are verified in the test suite. Custom agents from the wizard also export a Microsoft 365 declarative agent manifest.

### The playground as an MCP server

All three studios call the same MCP endpoint (`/mcp`) with a personal token from Admin → Settings. The tools are `list_models`, `usage_summary`, `list_blueprints`, `run_blueprint` and `search_knowledge`, so a flow built elsewhere still runs under the playground's policies, budgets and ledger.

## The code track

The notebook (runs end to end on mock data), the framework flavors (OpenAI Agents SDK, LangGraph, CrewAI, Microsoft Agent Framework, Google ADK), the deploy scripts (Azure AI Foundry, Anthropic Managed Agents, AWS AgentCore, Google Agent Engine) and the evaluation suites. See [NOTEBOOKS.md](NOTEBOOKS.md).

## The landscape

The Low-code studios page ends with a comparison of nine platforms: Copilot Studio, Langflow, n8n, Dify, Flowise, Power Automate, Microsoft Foundry Agent Service, Vertex AI Agent Builder and Amazon Bedrock AgentCore, with licence, hosting, MCP support, best fit and official links.

Licensing that matters for a subscription product: Langflow is MIT and can be bundled; n8n's Sustainable Use Licence permits internal self-hosting but not hosting n8n for third parties, so the playground generates workflows and links out; Dify's Apache 2.0 licence carries a multi-tenant restriction and a branding condition.

## Verification

`apps/api/tests/test_lowcode.py` checks the category split, that every Langflow edge joins real nodes on real fields with Langflow's own handle encoding, that every n8n connection references an existing node with a valid connection type and that gated blueprints include the review form, that the Copilot Studio recipe covers every blueprint step and links only to Microsoft Learn, and that the landscape has nine entries with official links. The Playwright suite exercises the page and the catalog categories.
