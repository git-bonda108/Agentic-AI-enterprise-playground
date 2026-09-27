# Delivery log

The playground was built in ten batches, then extended in a second series that turns it from a demonstration into a daily tool. A batch is complete when its pages are live, its tests pass and it has been exercised with real providers.

| Batch | Theme | Status |
| --- | --- | --- |
| 0 | Skeleton and design system | Done |
| 1 | Gateway, playground, ledger | Done |
| 2 | Model catalog, Smart routing, cost cockpit, admin | Done |
| 3 | Blueprint runtime and the first six blueprints | Done |
| 4 | Catalog import and Discover | Done |
| 5 | Notebooks, framework flavors, cloud deploy, no-code wizard | Done |
| 6 | Connectors, Knowledge Spaces, skills, the playground as an MCP server | Done |
| 7 | Evaluate, canary, hardening levels, agent versions with rollback | Done |
| 8 | Community, engagement, adoption analytics, platform agents | Done |
| 9 | Azure templates, CI, demo seed, security pass, control room, one-command launch | Done |
| 10 | Bring-your-own keys, platform key scope, thirteen more models across NVIDIA NIM, Mistral, xAI, Groq and Cohere | Done |
| 11 | Runnable notebooks: every blueprint ships an MVP notebook that executes end to end on mock data with minimal setup; compute picker, package installs, examples gallery | Done |
| 12 | Two ways to build: blueprints split into Gen AI and Agentic AI, each with a low-code track (Langflow flow, n8n workflow, Copilot Studio recipe) and a code track (notebook, framework flavor); low-code landscape page | Done |
| 13 | MCP Marketplace (Connectors reborn): client configuration generator, featured shelf, per-blueprint recommendations, the playground as a server for Langflow, n8n, Copilot Studio and Claude; Popular Git repos | Done |
| 14 | Agents that run on every framework in the sandbox, built-in tools, how-to panels, more platform agents, traces | Done |
| 15 | Cloud platforms: portal links, CLI sign-in, step-by-step deploy guides per framework and model | Done |
| 16 | Datasets section with mock data and trusted sources; cost and token drill-down; hours tiles on the console | Planned |
| 17 | Documentation hub and a full retest of every left-pane item | Planned |

## Batch 0: skeleton and design system

Monorepo with npm workspaces. Next.js 16, React 19, Tailwind 4, Base UI primitives, framer-motion. Dark-first palette (ink, violet, pink, cyan) with light mode, animated beam fields, command palette, sidebar with seven sections and batch badges, sign-in with Entra ID or seeded development users, authenticated API proxy. FastAPI service with health, metadata and the identity boundary. Playwright smoke and accessibility tests.

## Batch 1: gateway, playground, ledger

Streaming chat over server-sent events through LiteLLM. Parameters panel, system prompt, conversation list with pin and tags, markdown rendering, view code in five languages, compare up to four models. Usage ledger with tokens, cached tokens, cost and latency per call. Console home with a live ledger.

## Batch 2: catalog, routing, cost, admin

Fifteen-model catalog with prices, tiers, capabilities and lifecycle. Smart routing with a deterministic classifier, validated on a 100-prompt routing set at 90 percent or better. Cost cockpit with breakdowns by day, department, user, feature, model, provider and conversation. Admin pages for users, policies, budgets and settings. Alerts at 50, 80 and 100 percent with a hard stop.

## Batch 3: blueprint runtime

Blueprint primitives, LangGraph runtime with SQLite checkpoints, background execution, interrupt and resume that survive a restart. Six domain blueprints: document reconciliation, Sage Lens deep research, learning path, review panel, data analyst, knowledge Q&A. Deterministic mock datasets. Ten golden cases per blueprint. Agent Hub, run viewer with an animated graph and review inbox, Data page.

## Batch 4: catalog import and Discover

Importer that pulls agent definitions from everything-claude-code (67), gstack (31) and ruflo (37) into committed JSON with source and licence. Sixteen authored low-code templates and eighteen cloud sample mirrors. Curator that validates entries and grades them. Generic prompt-agent graph so every entry runs. Discover → Blueprints browser with families, search, detail and four faces per entry.

## Batch 5: faces

Notebooks page with JupyterLite in the browser and a metered server sandbox (local subprocess, Azure Container Apps dynamic sessions in production). Notebooks generated from blueprints, runs and conversations. Framework studio rendering any blueprint into five frameworks with offline smoke tests and zip download. Cloud studio with deploy scripts and pricing for four runtimes. No-code wizard with declarative agent export.

Verification at close: 52 API tests, 26 end-to-end tests, strict types and lint clean.

## Batch 6: connectors, knowledge, skills

Connectors: a committed snapshot of the official MCP registry (7,547 servers kept out of 36,000, filtered to complete, active entries plus well-known publishers) seeded into the database, with incremental admin sync, categories, approval workflow (pending, approved, blocked), a real MCP client that tests any remote server and lists its tools, and client configuration snippets. The playground is itself an MCP server: five tools (models, usage, blueprints, run a blueprint, search knowledge) behind personal access tokens, so Claude Desktop, Cursor or VS Code can drive it as a specific person under that person's policy and budget.

Knowledge Spaces: private, department or organisation-wide corpora with a chosen embedding model (local hashed vectors at no cost, or OpenAI and Gemini embeddings with their published prices), ingestion from pasted text, PDF, Word, Markdown, CSV, JSON, HTML, web pages, mock datasets and repositories, hybrid retrieval (cosine plus BM25 fused by reciprocal rank), and grounded answers through the Knowledge Q&A blueprint with every citation verified. Embeddings are metered on the ledger as their own feature.

Repository mapper: Python by syntax tree, TypeScript and JavaScript by pattern, Markdown by heading, into a graph of files, classes, functions, imports and calls with communities from label propagation, drawn as a force-directed map in the browser and searchable chunk by chunk. Local paths are limited to allowed roots; GitHub URLs are cloned shallowly.

Skills: 338 SKILL.md packs imported from everything-claude-code and ruflo with source and licence, categorised and searchable, attachable in the wizard. Attached skills join the system prompt at run time, ship as files in every generated framework project, and fold into the Copilot Studio manifest. Wizard agents can also call tools from approved connectors in a single tool round, and retrieve from Knowledge Spaces.

Verification at close: 64 API tests, 30 end-to-end tests, strict types, lint clean.

## Batch 7: evaluate

Evaluation suites: every built-in blueprint ships its ten golden cases as a system suite; a five-step guided builder creates suites for any agent from samples, real runs promoted into cases, or hand-written inputs with a phrase the answer must contain. Each step explains what it adds and why. Ten deterministic check types (status, contains, output keys and values, citations, cost, latency, review gates, anomaly codes) and a six-criterion rubric library (correctness, groundedness, completeness, format, tone, conciseness) scored one to five by an Economy-tier judge, metered as its own feature. A gate (minimum pass rate, cost per case, p95 latency) decides whether a run counts.

Canary: nightly reruns per suite from an in-process scheduler, compared with the last run that cleared its gate without drift. Drift on pass rate, cost or latency (with noise floors) raises an alert in the bell, demotes the agent a level, and, for wizard agents with automatic rollback on, restores the last good version. Every wizard edit keeps a numbered snapshot; manual rollback is one call.

Hardening ladder: Draft, Golden, Gated, Canaried, Production. Levels are computed from evidence (cases, evaluations, gate results, canary streaks); Production needs level 3 evidence plus an administrator's promotion, and a canary can take it away.

Verification at close: 69 API tests, 32 end-to-end tests, strict types and lint clean.

## Batch 8: community and adoption

Showcase: colleagues publish an agent, a run, a conversation or a suite with a title, a two-sentence summary, a one-line business outcome and tags; likes, comments, views, tag filters and a "most liked" sort. A platform agent, the showcase writer, drafts the post from the run so sharing a win takes one click; the author keeps the pen.

Challenges: an admin or champion opens a time-boxed build with a brief, shared cases and a rubric. Anyone submits an agent. Judging runs every entry through the evaluation engine on the same cases and rubric; the score is 60 percent rubric quality and 40 percent pass rate, so a fast wrong answer cannot win. Closing names the winner and awards the Champion badge.

Achievements and leaderboard: twelve badges unlocked only by evidence in the ledger and the evaluation engine (first prompt, comparer, smart saver, agent runner, reviewer, builder, librarian, evaluator, canary keeper, notebook hand, publisher, champion), each with progress. Leaderboards by person and by department over a window, with points from requests, outcomes, Smart routing savings, agents built, suites, likes received, badges and challenge wins.

Adoption analytics: hours per feature derived from ledger sessions, outcomes per feature, cost per outcome, estimated hours saved and value with admin-editable assumptions shown next to every number, an ROI matrix by department, weekly activity, and a second platform agent, the adoption digest, that writes a short narrative and three recommendations for a chosen audience.

Verification at close: 76 API tests, 35 end-to-end tests, strict types and lint clean.

## Batch 9: ship

Azure: a Bicep template for the full topology (Container Apps for web and API, PostgreSQL Flexible Server with pgvector, Redis, Key Vault, Container Registry, Log Analytics, a dynamic sessions pool, role assignments for the API's managed identity), a parameter file, and a deploy script that builds images in the cloud and runs a smoke test. Dockerfiles for both services; the web app builds as a Next.js standalone image.

CI: GitHub Actions with API tests and lint, web types, lint and the Playwright suite against a production build, gitleaks, npm audit and pip-audit, Bicep compilation, and container image builds on main.

Security pass: security headers on web and API, a per-caller rate limit, an internal-key check on every API route, and a start-up guard that refuses development defaults outside local environments. Documented in docs/SECURITY.md.

Demo seed: one script builds a tenant of ten people across departments with a month of governed usage, twelve runs, a Knowledge Space, two wizard agents, evaluations with canaries, showcase posts and a judged challenge, all generated offline. One command, `npm run start:local`, installs, seeds, starts both services and opens the browser.

Control room: a second view of any run in the playground palette, with three governed lanes (deterministic, agentic, governed), the record under review, the reasoning trace, the exception ledger and the outcome.

Diagrams rendered to docs/images (architecture, workflow, deployment, run flow) and a step-by-step demo script in docs/DEMO_SCRIPT.md.

Verification at close: 79 API tests, 38 end-to-end tests, strict types and lint clean, Bicep compiles.

## Batch 10: keys and models

Keys: a Keys drawer in the top bar, opened from anywhere a model needs a key. Each provider shows its status (your key with the last four characters, platform key, offline provider, not set), a link to the provider's key page, documentation and pricing, and add, test and remove actions. Personal keys are encrypted at rest with Fernet and never returned. Resolution order is personal key first, then the platform key; an admin switch in Settings decides whether platform keys serve everyone (pilot default) or only the product's own judge, canaries and platform agents. Availability, Smart routing, notebooks, agents and embeddings all resolve keys per caller, and every ledger row records which key paid, which the cost cockpit slices as a new layer.

Models: thirteen additions with prices from the providers' September 2026 sheets. NVIDIA NIM brings Nemotron 3 Nano, Super and Ultra, Hermes 4 405B, Llama 3.3 70B and Qwen3 235B on the free developer endpoint (rate limited); Mistral Medium 3.5, Large 3, Small 4 and Codestral; xAI Grok 4.7 and 4.3; Groq GPT-OSS 120B and 20B; Cohere Command A. The catalog now spans eleven providers and thirty models, and the Smart router's tier candidates include the new economy and workhorse options.

Deployment: the encryption key and the new provider keys are Key Vault secrets in the Bicep template, and the start-up guard requires the encryption key outside local environments.

Verification at close: 87 API tests, 43 end-to-end tests, strict types and lint clean, Bicep compiles.

## The second series in detail

The first ten batches proved the product. The second series turns it into a daily tool: everything runs, every path has a low-code and a code version, and every step ends with the official next link from the provider.

### Batch 11: runnable notebooks and blueprint MVPs

Every blueprint (six domain blueprints, the sixteen low-code templates, the wizard agents) ships a minimal viable notebook that runs end to end on the mock datasets with no configuration beyond a key from the Keys drawer. Notebooks open with a `playground` helper module already imported (chat, run blueprint, search knowledge, datasets) so the first cell works, and a run-on-open option executes the notebook as soon as it loads. A compute picker offers the browser runtime (free, no install), the playground sandbox (packages installable with `pip` from a cell, like an IDE), and external compute deep links: NVIDIA Brev launchables, Google Colab and GitHub Codespaces, each carrying the notebook. An examples gallery groups notebooks by blueprint and skill level. Activity metering records notebook time for the console.

### Batch 12: two ways to build

Blueprints are recategorised. **Gen AI blueprints** are single-model patterns: chat assistant, retrieval Q&A, extraction, classification, summarisation, content generation. **Agentic AI blueprints** are multi-step patterns with tools, memory, human review, loops and hand-offs: reconciliation, research, review panel, data analyst, learning path, plus the platform's own agents. Every blueprint carries two tracks.

The **low-code track** generates real artefacts: a Langflow flow (importable JSON with the same nodes, plus a "Run in Langflow" card with the install command, the import step and the MCP link back to the playground), an n8n workflow (importable JSON with an AI Agent node, the playground as an MCP Client Tool, and the equivalent connectors), and a Copilot Studio recipe (overview, instructions, what knowledge to add and from where, which tools to add and whether to use a Power Platform connector or an MCP server, the most suitable MCP servers, triggers and topics, and how the blueprint maps to workflow nodes: Classify, Extract, Agent, Human review, Connector, If/Else, Loop). Each recipe links to the exact Microsoft Learn page for the next step. The existing declarative agent manifest export stays.

The **code track** is the notebook from Batch 11 plus the five framework flavors and the deploy scripts.

A **low-code landscape** page compares Copilot Studio, Langflow, n8n, Dify, Flowise, Power Automate, Azure AI Foundry, Vertex AI Agent Builder and Bedrock Flows on licence, hosting, MCP support and best fit, each with its official link. Licensing matters for the subscription: Langflow is MIT and can be bundled; n8n's Sustainable Use Licence allows internal self-hosting but not hosting it for customers, so the playground generates n8n workflows and links out rather than embedding n8n; Dify's Apache 2.0 licence carries a multi-tenant restriction.

### Batch 12 as shipped

Delivered 2026-09-27. Every catalog entry carries a category. The rule: Role and Persona entries are Gen AI; Topology and Cloud entries are Agentic AI; Domain blueprints are Agentic AI when they have a human gate, two or more tool steps or two or more model steps (Knowledge Q&A is the one Gen AI domain blueprint); wizard agents are Agentic AI once they have connectors. The Blueprints page filters by category, every card shows its badge, and the detail dialog offers **Build it your way** with both tracks.

Discover → Low-code studios generates, for any runnable domain blueprint or low-code template, an importable Langflow flow, an importable n8n workflow and a Copilot Studio recipe, with the five steps to run each, the playground's MCP URL, the code track and the most suitable MCP servers (admin-approved and vendor-published servers ranked first; marketplaces that republish paid listings excluded). The page ends with the landscape of nine platforms.

Accuracy was verified against the real tools, not assumed. Langflow: flows are assembled from Langflow's own starter projects and from the MCP Tools component captured from a running Langflow 1.12.3, so every node carries the real component template; all six domain flows were uploaded through Langflow's `/api/v1/flows/upload/` endpoint and Langflow's build engine sorted and started executing the graph. n8n: node types, versions and parameter names (including the MCP Client Tool's `endpointUrl`, `serverTransport` and `authentication`, and the Wait node's form fields) were read from the installed n8n 2.40.7 node definitions, and all six workflows were imported with `n8n import:workflow`. Copilot Studio: every Microsoft Learn link the recipe cites returned 200 on 2026-09-27, including the Classify, Extract and Agent node pages and the Request for information (human review) page.

Verification at close: 120 API tests (15 new), 48 end-to-end tests, strict types and lint clean.

### Batch 13: MCP Marketplace and Popular Git repos

Connectors becomes **MCP Marketplace**: the same 7,547 registry entries with tiles, categories, a featured shelf, quality signals and admin approval, plus a configuration generator that produces the exact snippet for the client the person is using: Claude Desktop and Claude Code (`claude mcp add`), Cursor, VS Code, Copilot Studio (custom connector steps), Langflow (MCP client component) and n8n (MCP Client Tool node). Each blueprint recommends its most suitable servers. The playground's own MCP server appears as a tile with one-click configuration for each client, so a Langflow flow, an n8n workflow or a Copilot Studio agent can call the playground's models, blueprints and Knowledge Spaces. External directories (the official registry, mcpmarket.com, the awesome-mcp lists) are linked as sources.

**Popular Git repos** is a curated, categorised catalogue: agent frameworks and harnesses (superpowers, hermes-agent, OpenClaw, AutoGPT, ECC, claude-swarm, gstack, ruflo), visual builders (Langflow, n8n, Dify, Flowise), MCP (official servers, awesome-mcp lists, agentshield), knowledge tooling (graphify), evaluation and observability. Each tile shows stars and licence from a committed snapshot refreshed by a script, what it is for, how it relates to the playground (already used as a tile source, runnable as a flavor, installable as a skill) and the official link. Agentic AI blueprints can name **reference implementations**: public repositories (starting with github.com/git-bonda108) that show the pattern built for real, linked after the notebook so people can read, rate and discuss them through the showcase.

### Batch 11 as shipped

Delivered 2026-09-27. A `playground` helper module (standard library only, identical in the browser and in the sandbox) replaces the old inline helper: models, chat, compare, run with step trace, resume, datasets as rows or DataFrames, Knowledge Space search and ask, usage. Every generated notebook opens with one bootstrap cell that imports it; the browser runtime bundles it in its file drive and fetches it under the person's session if missing.

The Notebooks page opens on a gallery of twelve runnable notebooks grouped into Gen AI and Agentic AI with levels and minutes: six getting-started notebooks (hello, compare models, pandas with a narrator model and a package install, retrieval Q&A over a Knowledge Space, an agent that pauses for human review, a 40-line tool loop) and one MVP per domain blueprint that meets its data, runs it, reads the trace and output, handles the review gate and ends with next steps and reference implementations. The sandbox runs a whole notebook top to bottom in one process, shows every cell's output and stops at the first error; `%pip install` inside a cell or the Install box installs into a per-person environment that keeps the platform's packages visible. A compute picker offers the browser, the sandbox and external targets (NVIDIA Brev launchable deep link, Google Colab, GitHub Codespaces) with download-first guidance until the playground has a public address. Notebook time is measured through a zero-cost heartbeat.

Verification at close: 105 API tests (18 new, including one that starts a real HTTP server and executes all twelve notebooks in the sandbox), 46 end-to-end tests, strict types and lint clean. Live check: the hello notebook ran against real providers in 16 seconds with a Claude Sonnet reply metered at $0.0017.

### Batch 13 as shipped

Delivered 2026-09-27. Connectors became the **MCP Marketplace**: the same 7,547 registry entries with a featured shelf (the playground first, then admin-approved servers by signal), links to the external directories, and, on every tile, **Connect from** tabs that generate configuration for Claude Desktop, Claude Code, Cursor, VS Code, Copilot Studio, Langflow and n8n from the server's registry entry, each in the client's own format with the steps around it and the vendor's documentation page. Secrets stay placeholders. The playground's own server carries the same seven configurations, so any of those clients can run blueprints and search Knowledge Spaces under the caller's policy and ledger. Every client documentation URL and directory URL was checked to resolve when the batch shipped.

**Popular Git repos** is a new Discover page: a curated, categorised catalogue of 60 repositories (34 chosen for what they mean to the playground, plus the author's 26 public repositories as reference implementations) with stars, forks, licence, language and last activity from GitHub, a sentence on what each is for, how it relates to the playground, and official links. The snapshot is committed and refreshed by `npm run import:repos`; repositories GitHub could not find would have been dropped, and three that had been renamed were recorded under their current names.

Verification at close: 124 API tests (4 new), 50 end-to-end tests (2 new), strict types and lint clean.

### Batch 14 as shipped

Delivered 2026-09-27. The playground now exposes an **OpenAI-compatible gateway** at `/openai/v1`: any SDK that speaks the Chat Completions API (OpenAI, OpenAI Agents SDK, LangChain and LangGraph, CrewAI, Microsoft Agent Framework, Google ADK through LiteLLM) uses the playground as its provider with a personal token, and every call gets Smart routing, the role policy, the budget, personal or platform keys, metering as feature `sdk`, and a trace grouped by `X-Trace-Id`. Streaming, tool calls and content parts are supported; errors use the OpenAI error shape. Every framework project on the Frameworks page now points at the gateway and needs no provider key; two buttons run it in the sandbox (the offline smoke test, or a live run that installs the SDK, mints a short-lived token, executes `agent.py` through the gateway and removes the token).

**Built-in tools** for wizard agents: current date, exact arithmetic, dataset queries, knowledge search, public web fetch (private and local addresses blocked) and sandboxed Python, executed inside the API with the caller's identity alongside MCP connectors. Four more **platform agents**: Key health check (probes every platform key, alerts on rejection), Cost sentinel (last day against the trailing week per department and feature, alerts on jumps), Connector reviewer (approve, hold or block recommendations for the marketplace queue) and Onboarding coach (next three steps from a person's own ledger), each with ten golden cases. A **Traces** page lists runs, SDK sessions and chats with timelines of steps beside metered calls. **How-to** panels on nine pages give the steps for that page and the vendor documentation.

Found live and fixed before shipping: an SDK that omits `max_tokens` used to receive the policy ceiling, which Anthropic rejects above a model's maximum; the gateway now defaults to 4,096 within the policy cap. Live check with real keys: the OpenAI Python SDK listed models, completed through Smart routing on Claude Haiku, streamed, and returned a real tool call from Claude Sonnet, all visible in Traces.

Verification at close: 143 API tests (19 new, one skipped where the LangGraph SDK is not installed), 53 end-to-end tests, strict types and lint clean.


### Batch 15 as shipped

Delivered 2026-09-27. The Clouds page became **Cloud platforms**: Microsoft Foundry hosted agents, AWS Bedrock AgentCore Runtime, Google Cloud Agent Runtime and Anthropic Managed Agents, each with its portal link, the CLI install commands per operating system, the exact sign-in commands (`azd auth login` and `az login`; `aws configure sso` and `aws sso login`; `gcloud auth login` and `gcloud auth application-default login`; an Anthropic API key with the `ant` CLI), a verify command, the roles the identity needs, the fit of each of the five framework projects (first-class, sample, bring your own, harness) and the providers whose models the cloud sells natively. A **step-by-step deploy guide** builder takes a blueprint, a framework, a catalog model and a model mode and returns eight ordered steps with copyable commands and the official page for each: sign in to the portal, install the CLI and sign in, run the project once locally, choose where the model lives, scaffold, test locally, deploy and invoke, clean up. Gateway mode keeps the deployed agent governed and metered by the playground; native mode points it at the cloud's own model and falls back with an explanation when the cloud does not sell that provider. The guide downloads as markdown. The deploy scripts were refreshed to the npm AgentCore CLI and to `ant apply`, and a self-hosting section explains how to run the playground on an Azure subscription with `infra/deploy.sh` (no public Deploy to Azure button, the repository is private). Every command in every guide, sign-in block and script is parsed with `bash -n` in the tests. Docs: `docs/CLOUD_PLATFORMS.md`.
### Batches 15 to 17

Unchanged from the earlier plan: Datasets, cost and token drill-down, console hours tiles (16); documentation hub and full retest (17).

