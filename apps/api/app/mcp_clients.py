"""Per-client configuration for any MCP server in the marketplace.

Each client has its own file, command or wizard. The shapes below follow each client's documentation as of September 2026:
Claude Desktop reads `claude_desktop_config.json` (stdio servers; remote servers go through Settings → Connectors or the
`mcp-remote` bridge), Claude Code has `claude mcp add`, Cursor reads `~/.cursor/mcp.json`, VS Code reads `.vscode/mcp.json`
with a `servers` map, Copilot Studio adds remote servers through its MCP wizard, Langflow accepts the standard `mcpServers`
JSON in a project's MCP Server tab, and n8n's MCP Client Tool node takes an endpoint URL over streamable HTTP or SSE.
"""

from __future__ import annotations

import json
from itertools import chain

TOKEN_PLACEHOLDER = "pgk_PASTE_YOUR_PERSONAL_TOKEN"

CLIENT_DOCS = {
    "claude-desktop": "https://modelcontextprotocol.io/docs/develop/connect-local-servers",
    "claude-code": "https://code.claude.com/docs/en/mcp",
    "cursor": "https://cursor.com/docs/context/mcp",
    "vscode": "https://code.visualstudio.com/docs/copilot/customization/mcp-servers",
    "copilot-studio": "https://learn.microsoft.com/en-us/microsoft-copilot-studio/mcp-add-existing-server-to-agent",
    "langflow": "https://docs.langflow.org/mcp-client",
    "n8n": "https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.toolmcp/",
}


def _stdio(c: dict) -> dict | None:
    """The command a stdio server is started with, from its registry package, or None for remote servers."""
    if c.get("transport") == "remote":
        return None
    pkg = c.get("package") or {}
    ident = pkg.get("identifier") or c["id"].split("/")[-1]
    registry = (pkg.get("registry") or c.get("transport") or "").lower()
    if registry in ("npm", "npmjs"):
        cfg: dict = {"command": "npx", "args": ["-y", ident]}
    elif registry in ("pypi", "pip"):
        cfg = {"command": "uvx", "args": [ident]}
    elif registry in ("oci", "docker"):
        cfg = {"command": "docker", "args": ["run", "-i", "--rm", *chain.from_iterable(["-e", v] for v in (c.get("env_vars") or [])), ident]}
    elif registry == "mcpb":
        return {"command": "mcpb", "args": [ident], "note": "An MCP bundle: install it from Claude Desktop → Settings → Extensions"}
    else:
        cfg = {"command": ident, "args": []}
    if c.get("env_vars"):
        cfg["env"] = {v: f"<{v}>" for v in c["env_vars"]}
    return cfg


def _headers(c: dict) -> dict[str, str]:
    if c.get("id") == "playground/mcp":
        return {"Authorization": f"Bearer {TOKEN_PLACEHOLDER}"}
    return {v: f"<{v}>" for v in (c.get("env_vars") or [])}


def _key(c: dict) -> str:
    return "enterprise-ai-playground" if c.get("id") == "playground/mcp" else c["id"].split("/")[-1]


def client_configs(c: dict) -> list[dict]:
    """One entry per client: a snippet in the client's own format, the steps around it and the documentation page."""
    key, url, stdio, headers = _key(c), c.get("remote_url") or "", _stdio(c), _headers(c)
    remote = stdio is None
    playground = c.get("id") == "playground/mcp"
    token_step = "Create a personal token in the playground (Admin → Settings → Personal tokens) and paste it in place of the placeholder." if playground else ("Fill in the secrets the server needs: " + ", ".join(c.get("env_vars") or []) + "." if c.get("env_vars") else "No secrets are required.")
    out: list[dict] = []

    # Claude Desktop
    if remote:
        desktop = {"mcpServers": {key: {"command": "npx", "args": ["-y", "mcp-remote", url, *chain.from_iterable(["--header", f"{k}: {v}"] for k, v in headers.items())]}}}
        desktop_steps = ["Settings → Connectors → Add custom connector, paste the server URL and finish the sign-in if the server asks for one (simplest).", "Or add the entry below to claude_desktop_config.json (Settings → Developer → Edit Config); the mcp-remote bridge speaks to remote servers from a stdio client.", token_step, "Restart Claude Desktop; the server's tools appear under the tools menu."]
    else:
        desktop = {"mcpServers": {key: {k: v for k, v in stdio.items() if k != "note"}}}
        desktop_steps = ["Settings → Developer → Edit Config opens claude_desktop_config.json.", "Add the entry below inside mcpServers.", token_step, "Restart Claude Desktop; the server's tools appear under the tools menu."]
    out.append({"client": "claude-desktop", "name": "Claude Desktop", "format": "json", "file": "claude_desktop_config.json", "snippet": json.dumps(desktop, indent=2), "steps": desktop_steps, "docs": CLIENT_DOCS["claude-desktop"]})

    # Claude Code
    if remote:
        cmd = f"claude mcp add --transport http {key} {url}" + "".join(f' --header "{k}: {v}"' for k, v in headers.items())
    else:
        env = "".join(f" --env {k}={v}" for k, v in (stdio.get("env") or {}).items())
        cmd = f"claude mcp add {key}{env} -- {stdio['command']} {' '.join(stdio.get('args') or [])}".rstrip()
    out.append({"client": "claude-code", "name": "Claude Code", "format": "bash", "file": "", "snippet": cmd, "steps": ["Run the command in the project where you want the server (add --scope user to keep it across projects).", token_step, "Run /mcp inside Claude Code to check the connection and list the tools."], "docs": CLIENT_DOCS["claude-code"]})

    # Cursor
    cursor = {"mcpServers": {key: ({"url": url, **({"headers": headers} if headers else {})} if remote else {k: v for k, v in stdio.items() if k != "note"})}}
    out.append({"client": "cursor", "name": "Cursor", "format": "json", "file": "~/.cursor/mcp.json (or .cursor/mcp.json in the project)", "snippet": json.dumps(cursor, indent=2), "steps": ["Cursor Settings → MCP → Add new global MCP server opens the file.", "Add the entry below inside mcpServers.", token_step, "Toggle the server on; its tools show in the MCP settings list and in Agent mode."], "docs": CLIENT_DOCS["cursor"]})

    # VS Code (GitHub Copilot agent mode)
    vscode = {"servers": {key: ({"type": "http", "url": url, **({"headers": headers} if headers else {})} if remote else {"type": "stdio", **{k: v for k, v in stdio.items() if k != "note"}})}}
    out.append({"client": "vscode", "name": "VS Code", "format": "json", "file": ".vscode/mcp.json", "snippet": json.dumps(vscode, indent=2), "steps": ["Command Palette → MCP: Add Server, or create .vscode/mcp.json with the entry below.", "Prefer an inputs entry for secrets so they are prompted for rather than committed.", token_step, "Open Copilot Chat in agent mode and pick the server's tools from the tools menu."], "docs": CLIENT_DOCS["vscode"]})

    # Copilot Studio
    if remote:
        cs_steps = ["Open the agent → Tools → Add a tool → Model Context Protocol → Add an existing MCP server.", f"Server URL: {url}. Authentication: " + ("API key (Authorization header) with your personal token." if playground else ("API key or OAuth as the server documents." if headers else "None.")), "Generative orchestration must be on; the server's tools and resources then appear automatically and stay in sync.", "Publish the connector across the tenant if other makers need it."]
        cs_snippet = f"Server URL: {url}\nTransport: streamable HTTP\nAuthentication: " + ("API key: Authorization = Bearer <personal token>" if playground else (", ".join(headers) if headers else "none"))
    else:
        cs_steps = ["Copilot Studio connects to remote MCP servers only. Host this stdio server behind an HTTPS endpoint (for example an MCP gateway or a container with an HTTP transport), then add it as an existing MCP server.", "Alternatively create a new MCP server with the wizard and expose the same tools.", "Generative orchestration must be on for tools to be selected automatically."]
        cs_snippet = f"Local command: {stdio['command']} {' '.join(stdio.get('args') or [])}\nExpose it over HTTPS before adding it to Copilot Studio."
    out.append({"client": "copilot-studio", "name": "Copilot Studio", "format": "text", "file": "", "snippet": cs_snippet, "steps": cs_steps, "docs": CLIENT_DOCS["copilot-studio"]})

    # Langflow
    langflow = {"mcpServers": {key: ({"url": url, **({"headers": headers} if headers else {})} if remote else {k: v for k, v in stdio.items() if k != "note"})}}
    out.append({"client": "langflow", "name": "Langflow", "format": "json", "file": "Project → MCP Server tab → Add MCP server (JSON)", "snippet": json.dumps(langflow, indent=2), "steps": ["In a Langflow project open the MCP Server tab and add a server by pasting the JSON below.", "Drop the MCP Tools component on the canvas, pick the server, then enable Tool Mode and connect it to an Agent.", token_step, "The Agent lists the server's tools by name; edit their descriptions under Actions if the agent picks the wrong one."], "docs": CLIENT_DOCS["langflow"]})

    # n8n
    if remote:
        n8n = {"parameters": {"endpointUrl": url, "serverTransport": "httpStreamable", "authentication": "bearerAuth" if playground else ("headerAuth" if headers else "none"), "include": "all"}, "type": "@n8n/n8n-nodes-langchain.mcpClientTool", "typeVersion": 1.2}
        n8n_steps = ["Add an MCP Client Tool node to an AI Agent's tool input with the parameters below.", "Create the credential the authentication field asks for (Bearer with your personal token, or a header credential).", "The agent discovers the tools on first run; restrict them with Tools to Include if needed."]
    else:
        n8n = {"parameters": {"endpointUrl": "http://localhost:8000/mcp", "serverTransport": "httpStreamable", "authentication": "none", "include": "all"}, "type": "@n8n/n8n-nodes-langchain.mcpClientTool", "typeVersion": 1.2}
        n8n_steps = ["n8n's MCP Client Tool connects to remote endpoints. Expose this stdio server over HTTP first, for example with the supergateway bridge: npx -y supergateway --stdio \"" + f"{stdio['command']} {' '.join(stdio.get('args') or [])}" + "\" --outputTransport streamableHttp --port 8000.", "Then add an MCP Client Tool node with the endpoint below to an AI Agent."]
    out.append({"client": "n8n", "name": "n8n", "format": "json", "file": "MCP Client Tool node", "snippet": json.dumps(n8n, indent=2), "steps": n8n_steps, "docs": CLIENT_DOCS["n8n"]})
    return out


DIRECTORIES = [
    {"name": "Official MCP registry", "url": "https://registry.modelcontextprotocol.io", "blurb": "The source of this marketplace: publishers register servers with packages, remotes and metadata."},
    {"name": "MCP Market", "url": "https://mcpmarket.com", "blurb": "A large directory of servers, clients and agent skills with categories and popularity."},
    {"name": "awesome-mcp-servers (punkpeye)", "url": "https://github.com/punkpeye/awesome-mcp-servers", "blurb": "Community-curated list by category."},
    {"name": "Microsoft MCP servers", "url": "https://github.com/microsoft/mcp", "blurb": "Azure, Microsoft 365 and developer tooling servers from Microsoft."},
    {"name": "AWS MCP servers", "url": "https://github.com/awslabs/mcp", "blurb": "Servers for AWS services from AWS Labs."},
]
