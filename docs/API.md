# API reference

All routes require the internal key and identity headers, which the web application's proxy adds automatically. Direct callers must send `X-Internal-Key`, `X-User-Id` and `X-User-Email`, and may send `X-User-Name`, `X-User-Role` and `X-User-Department`. Interactive documentation is served at `/docs` while the API runs.

## Health and metadata

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness, environment and provider mode |
| GET | `/v1/meta` | Application name, version, current batch, sections |

## Models and routing

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/models` | Catalog with prices, tiers, capabilities and availability for the caller; each model carries `key_source` (`personal`, `platform`, `fake` or `none`) |
| POST | `/v1/route/preview` | Classify a prompt and show the model Smart routing would pick, with expected savings |

## Chat and conversations

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/v1/chat/stream` | Streaming completion over server-sent events: `meta`, `delta`, `usage`, `error`, `done` |
| POST | `/v1/chat/complete` | Blocking completion for notebooks and scripts |
| GET, POST | `/v1/conversations` | List or create |
| GET, PATCH, DELETE | `/v1/conversations/{id}` | Read, rename, tag, pin, delete |

## Usage and alerts

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/usage/summary` | Credits, spend this month, tokens, models used, recent events |
| GET | `/v1/usage/breakdown` | Spend by `day`, `department`, `user`, `feature`, `model`, `provider` or `conversation` |
| GET | `/v1/alerts` | Budget alerts for the caller |
| POST | `/v1/alerts/{id}/ack` | Acknowledge an alert |

## Administration

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/admin/users` | People, roles, departments |
| PATCH | `/v1/admin/users/{id}` | Change role or department |
| GET | `/v1/admin/policies` | Model policy per role |
| PUT | `/v1/admin/policies/{role}` | Replace a role's policy |
| POST | `/v1/admin/policies/reset` | Restore defaults |
| GET, PUT | `/v1/admin/budgets` | Budgets at organisation, department, user and user-default scope |
| GET | `/v1/admin/budgets/me` | The caller's own cap and spend |
| GET | `/v1/admin/settings` | Providers, keys present, environment |

## Blueprints, runs and data

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/blueprints` | Runnable blueprints with manifests |
| GET | `/v1/blueprints/{id}` | One manifest |
| GET | `/v1/data` | Mock datasets with previews |
| POST | `/v1/runs` | Start a run; `wait=true` blocks until it completes or pauses |
| GET | `/v1/runs` | Runs visible to the caller |
| GET | `/v1/runs/{id}` | Run with steps, review payload and output |
| POST | `/v1/runs/{id}/resume` | Answer a review gate |

## Catalog

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/catalog` | Entries across families, with `family`, `q` and `runnable` filters |
| GET | `/v1/catalog/stats` | Totals, per-family counts, curation grades |
| GET | `/v1/catalog/{id}` | Entry with instructions and provenance |
| POST | `/v1/catalog/curate` | Re-run the curator (admin) |

## Faces

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/notebooks/blank.ipynb` | Empty notebook with the playground helper |
| GET | `/v1/notebooks/blueprint/{id}.ipynb` | Notebook that runs a blueprint |
| GET | `/v1/notebooks/run/{id}.ipynb` | Notebook reconstructed from a run |
| GET | `/v1/notebooks/conversation/{id}.ipynb` | Notebook reconstructed from a conversation |
| POST | `/v1/sandbox/execute` | Execute code in the server sandbox; metered as `notebook` |
| GET | `/v1/frameworks` | Supported frameworks with install, docs, licence and hosting notes |
| GET | `/v1/blueprints/{id}/flavor/{framework}` | Generated project files |
| GET | `/v1/blueprints/{id}/flavor/{framework}/download` | The same project as a zip |
| GET | `/v1/clouds` | Supported cloud runtimes with pricing and prerequisites |
| GET | `/v1/blueprints/{id}/deploy/{cloud}` | Deploy script |
| GET, POST | `/v1/custom-agents` | Agents built in the wizard |
| DELETE | `/v1/custom-agents/{id}` | Remove one of your agents |
| GET | `/v1/custom-agents/{id}/export/declarative-agent` | Microsoft 365 declarative agent manifest |

## Connectors

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/connectors` | Registry snapshot with `q`, `category`, `transport`, `approval`, `publisher` filters and paging |
| GET | `/v1/connectors/stats` | Totals by approval, transport and category |
| POST | `/v1/connectors/sync` | Incremental sync from the official registry (admin) |
| GET | `/v1/connectors/{id}` | One connector with its client configuration |
| POST | `/v1/connectors/{id}/approval` | Approve, block or reset a connector (admin) |
| POST | `/v1/connectors/{id}/probe` | Connect to a remote server and list its tools |
| POST | `/v1/connectors/{id}/call` | Call one tool on an approved remote server |

## MCP server and tokens

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/mcp` | The playground as an MCP server (JSON-RPC over HTTP): `initialize`, `ping`, `tools/list`, `tools/call` |
| GET, POST | `/v1/tokens` | Personal access tokens for external MCP clients; the value is returned once |
| DELETE | `/v1/tokens/{id}` | Revoke a token |

## Knowledge Spaces

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/knowledge/embedding-models` | Embedding models with price and availability |
| GET, POST | `/v1/knowledge/spaces` | Visible spaces; create one |
| GET, DELETE | `/v1/knowledge/spaces/{id}` | Space with documents; delete |
| POST | `/v1/knowledge/spaces/{id}/documents/text` | Add pasted text |
| POST | `/v1/knowledge/spaces/{id}/documents/file` | Add a file (base64) in PDF, Word, Markdown, text, CSV, JSON or HTML |
| POST | `/v1/knowledge/spaces/{id}/documents/url` | Add a web page |
| POST | `/v1/knowledge/spaces/{id}/documents/dataset` | Add a mock dataset, one chunk per record |
| POST | `/v1/knowledge/spaces/{id}/documents/repo` | Map a repository into a graph and chunks |
| DELETE | `/v1/knowledge/spaces/{id}/documents/{doc}` | Remove a document |
| GET | `/v1/knowledge/spaces/{id}/graph` | Merged graph of mapped repositories |
| POST | `/v1/knowledge/spaces/{id}/search` | Hybrid search |
| POST | `/v1/knowledge/spaces/{id}/ask` | Grounded answer through the Knowledge Q&A blueprint |

## Skills

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/skills` | Skills with `q`, `source`, `category` filters |
| GET | `/v1/skills/stats` | Totals by category and source |
| GET | `/v1/skills/{id}` | One skill with its full body |

## Evaluate

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/evals/library` | Rubric criteria, deterministic check types, hardening levels, defaults |
| GET, POST | `/v1/evals/suites` | Suites (system and yours); create one |
| GET, PATCH, DELETE | `/v1/evals/suites/{id}` | Suite with last run, canary and hardening ladder |
| POST | `/v1/evals/suites/{id}/cases/from-run` | Promote a real run into a golden case |
| POST | `/v1/evals/suites/{id}/run` | Evaluate every case; `wait=true` blocks |
| GET | `/v1/evals/runs` | Evaluation runs with `suite_id`, `blueprint_id`, `kind` filters |
| GET | `/v1/evals/runs/{id}` | Per-case checks, scores and drift |
| GET, PUT | `/v1/evals/suites/{id}/canary` | Nightly schedule, thresholds, automatic rollback |
| POST | `/v1/evals/suites/{id}/canary/run` | Run the canary now |
| GET | `/v1/evals/canary` | Canary board with last run and hardening level |
| POST | `/v1/evals/canary/tick` | Run due canaries (admin; `force=true` runs all) |
| GET | `/v1/evals/hardening` | Ladders for every evaluated agent, or one with `blueprint_id` |
| POST | `/v1/evals/hardening/{id}/promote` | Promote or demote (admin) |
| PATCH | `/v1/custom-agents/{id}` | Edit a wizard agent; the previous state becomes a numbered version |
| GET | `/v1/custom-agents/{id}/versions` | Version history |
| POST | `/v1/custom-agents/{id}/rollback` | Restore a version |

## Community

| Method | Path | Purpose |
| --- | --- | --- |
| GET, POST | `/v1/community/showcase` | Published items with `q`, `tag`, `sort`; publish one |
| POST | `/v1/community/showcase/draft` | The showcase writer agent drafts a post from a run or a sentence |
| GET, DELETE | `/v1/community/showcase/{id}` | Item with comments; unpublish |
| POST | `/v1/community/showcase/{id}/like` | Toggle a like |
| POST | `/v1/community/showcase/{id}/comments` | Comment |
| GET, POST | `/v1/community/challenges` | Challenges; open one (admin or champion) |
| GET | `/v1/community/challenges/{id}` | Brief, cases, rubric, submissions and standings |
| POST | `/v1/community/challenges/{id}/submit` | Enter an agent |
| POST | `/v1/community/challenges/{id}/judge` | Judge pending entries with the evaluation engine |
| POST | `/v1/community/challenges/{id}/close` | Close and award the badge |
| GET | `/v1/community/me` | Achievements with progress, rank and points |
| GET | `/v1/community/leaderboard` | Rows by `user` or `department` over `days` |

## Adoption

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/adoption/summary` | Hours per feature, outcomes, cost per outcome, ROI matrix, weekly series, assumptions |
| GET, PUT | `/v1/adoption/assumptions` | Minutes saved per outcome and hourly value (admin edits) |
| POST | `/v1/adoption/digest` | The adoption digest agent writes a narrative with recommendations |

## Provider keys

People bring their own provider keys, as in the OpenAI or Claude playgrounds. A personal key is encrypted at rest (Fernet, `PLAYGROUND_KEY_ENCRYPTION_KEY`) and only its last four characters are ever returned. Resolution for a call: the caller's personal key for the provider first; otherwise the platform key from the API environment when the admin scope allows it. The judge, canaries and platform agents always use platform keys.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/v1/keys` | One row per provider: source (`personal`, `platform`, `fake`, `none`), last four characters of a personal key, the key page, docs and pricing links, model count; plus the admin scope |
| PUT | `/v1/keys/{provider}` | Save or replace a personal key (`key`, optional `api_base` for Azure OpenAI). Prefix is validated per provider |
| DELETE | `/v1/keys/{provider}` | Remove the personal key |
| POST | `/v1/keys/{provider}/test` | One tiny completion on the provider's cheapest model with the key that would serve the caller |
| PUT | `/v1/keys/admin/scope` | Admin: `all` (platform keys serve everyone; pilot default) or `platform-only` (people bring their own) |

Every ledger row records `key_source`, and `/v1/usage/breakdown?by=key_source` splits spend between personal and platform keys.

## Limits and headers

Every response carries `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` and `Cache-Control: no-store`. Callers are limited to 240 requests a minute; a 429 carries `Retry-After`, and successful responses carry `X-RateLimit-Limit` and `X-RateLimit-Remaining`.

## Error conventions

| Status | Meaning |
| --- | --- |
| 401 | Missing internal key or identity |
| 402 | Budget exhausted; the call was not sent to the provider |
| 403 | Model not allowed by the caller's role policy |
| 404 | Unknown model, blueprint, run or conversation |
| 429 | Rate limit reached for this caller |
| 502 | Provider error, with the provider's message |
