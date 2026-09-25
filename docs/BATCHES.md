# Delivery log

The playground is built in ten batches. A batch is complete when its pages are live, its tests pass and it has been exercised with real providers.

| Batch | Theme | Status |
| --- | --- | --- |
| 0 | Skeleton and design system | Done |
| 1 | Gateway, playground, ledger | Done |
| 2 | Model catalog, Smart routing, cost cockpit, admin | Done |
| 3 | Blueprint runtime and the first six blueprints | Done |
| 4 | Catalog import and Discover | Done |
| 5 | Notebooks, framework flavors, cloud deploy, no-code wizard | Done |
| 6 | Connectors, Knowledge Spaces, skills | In progress |
| 7 | Evaluate, canary, hardening levels | Planned |
| 8 | Community, engagement, adoption analytics | Planned |
| 9 | Azure templates, CI, demo seed, security pass | Planned |

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

Scope: connectors synchronised from the official MCP registry with admin approval and live connection tests; the playground itself exposed as an MCP server; Knowledge Spaces with chunking, embeddings, hybrid search and grounded answers; a repository mapper that turns code into a navigable graph; a skills library imported from public SKILL.md packs, attachable to any agent; wizard and framework exports updated to carry connectors, knowledge and skills.

## Batch 7: evaluate

Guided creation of golden sets and rubrics, evaluation runs with per-case scores, nightly canary reruns with drift alerts and rollback, and hardening levels that an agent is promoted through.

## Batch 8: community and adoption

Showcase of published agents, challenges with rubric judging, leaderboards, achievements, and adoption analytics: hours per feature, cost per outcome, ROI by team.

## Batch 9: ship

Bicep templates for the Azure topology, CI pipeline, demo seed data, security review, operational runbook.
