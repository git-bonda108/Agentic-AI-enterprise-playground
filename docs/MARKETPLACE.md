# MCP Marketplace and Popular Git repos

## MCP Marketplace

Discover → MCP Marketplace lists 7,547 servers from the official MCP registry snapshot (quality-filtered at import: active, with a package or a remote endpoint and enough metadata), with categories, transports, publisher and admin approval. Agents may only call approved servers; the playground itself is a server in the list.

**Featured shelf.** The playground's own server first, then admin-approved servers by signal strength. Below it, links to external directories: the official registry, MCP Market, the awesome-mcp-servers list, and the Microsoft and AWS server catalogs.

**Connect from.** Every tile carries ready-made configuration for seven clients, generated from the server's registry entry (remote URL or package) in each client's own format:

| Client | What you get | Where it goes |
| --- | --- | --- |
| Claude Desktop | `mcpServers` JSON; remote servers via Settings → Connectors or the `mcp-remote` bridge | `claude_desktop_config.json` |
| Claude Code | `claude mcp add …` (`--transport http` and `--header` for remote servers, `-- command args` for stdio) | Terminal |
| Cursor | `mcpServers` JSON with `url` and `headers`, or `command` and `args` | `~/.cursor/mcp.json` |
| VS Code | `servers` JSON with `type: http` or `type: stdio` | `.vscode/mcp.json` |
| Copilot Studio | Wizard steps for "Add an existing MCP server" (remote servers only; stdio servers must be hosted first) | Copilot Studio → Tools |
| Langflow | `mcpServers` JSON for a project's MCP Server tab, then the MCP Tools component in tool mode | Langflow project |
| n8n | MCP Client Tool node parameters (`endpointUrl`, `serverTransport`, `authentication`); stdio servers via the supergateway bridge | AI Agent tool input |

Secrets are never filled in: personal tokens for the playground and API keys for other servers appear as placeholders, and the steps say where to get them. The documentation link on each tab is the client vendor's own page; all of them are verified in the test suite to be HTTPS links and were checked to resolve when this batch shipped.

**The playground as a server.** The tools are `list_models`, `usage_summary`, `list_blueprints`, `run_blueprint` and `search_knowledge`. Create a personal token in Admin → Settings → Personal tokens, paste it in place of the placeholder, and every call from Claude, Cursor, VS Code, Copilot Studio, Langflow or n8n runs under your policy, budget and ledger.

## Popular Git repos

Discover → Popular Git repos is a curated catalogue of the repositories behind the playground and the ones worth knowing next to it, grouped into: reference implementations (the author's public repositories, which the notebooks and Agentic AI blueprints link to as worked examples), agent frameworks and SDKs, harnesses and skills, visual builders, MCP, knowledge tooling, and evaluation and observability. Each tile shows stars, forks, licence, language and last activity from GitHub, what the repository is for, how it relates to the playground, and the official links.

The snapshot lives in `apps/api/catalog/repos.json` and is refreshed by hand with `npm run import:repos` (GitHub token required at import time only; the API never calls GitHub). Repositories GitHub does not know are reported and left out rather than invented; renamed repositories are recorded under their current name.
