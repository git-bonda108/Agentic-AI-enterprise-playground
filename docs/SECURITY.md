# Security

What protects the playground, layer by layer, and what a reviewer should verify.

## Boundaries

| Boundary | Control | Where |
| --- | --- | --- |
| Browser to web | Entra ID OpenID Connect, HTTP-only session cookie, CSRF handled by Auth.js | `apps/web/src/auth.ts` |
| Web to API | Shared internal key in a header, at least 24 characters in production; identity asserted only by the web tier; the API has internal ingress only | `apps/api/app/auth.py`, `infra/bicep/main.bicep` |
| External MCP clients to API | Personal access tokens, shown once, stored as SHA-256, revocable; every call metered to the owner | `apps/api/app/routers/mcp.py` |
| API to providers | Keys in environment variables sourced from Key Vault; never persisted or returned | `apps/api/app/llm.py` |
| Model access | Role policies checked before every call | `apps/api/app/governance.py` |
| Spend | Budgets with alerts at 50, 80 and 100 percent and a hard stop | `apps/api/app/governance.py` |
| Code execution | Browser (Pyodide) or Container Apps dynamic sessions with egress disabled; locally an isolated subprocess | `apps/api/app/notebooks.py` |
| Repository mapping | Local paths limited to allowed roots; GitHub URLs cloned shallowly into a temporary directory | `apps/api/app/repo_map.py` |
| Connectors | Admin approval before an agent may call a server; probes never store credentials | `apps/api/app/connectors.py` |

## Headers and limits

- Web responses carry `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (SAMEORIGIN only for the notebook runtime path), `Referrer-Policy`, `Permissions-Policy` and HSTS. `X-Powered-By` is removed.
- API responses carry `nosniff`, `DENY`, `no-referrer`, `Cache-Control: no-store` and HSTS behind TLS.
- The API rate-limits each caller to 240 requests a minute (configurable with `PLAYGROUND_RATE_LIMIT_PER_MINUTE`) and answers 429 with `Retry-After`.
- CORS is limited to the web app's origin.

## Start-up guard

Outside `local`, `e2e`, `test` and `development` environments the API refuses to start when the internal key is the development default or too short, the fake provider is on, the database is SQLite, or a plain-http CORS origin is configured.

## Secrets hygiene

- `.env` is ignored by git; `.env.example` contains placeholders only.
- CI runs gitleaks over the full history on every push, plus `npm audit` and `pip-audit`.
- Personal tokens and the internal key never appear in logs or responses after creation.

## What is out of scope for the pilot

SOC 2 evidence collection, Purview integration and Event Hub streaming were deliberately left for a later phase. The ledger already holds every event needed to feed them.

## Reporting

Report a suspected weakness to the repository owner with steps to reproduce. Do not open a public issue for an unpatched problem.
