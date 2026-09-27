# Security

What protects the playground, layer by layer, and what a reviewer should verify.

## Boundaries

| Boundary | Control | Where |
| --- | --- | --- |
| Browser to web | Entra ID OpenID Connect, HTTP-only session cookie, CSRF handled by Auth.js | `apps/web/src/auth.ts` |
| Web to API | Shared internal key in a header, at least 24 characters in production; identity asserted only by the web tier; the API has internal ingress only | `apps/api/app/auth.py`, `infra/bicep/main.bicep` |
| External MCP clients to API | Personal access tokens, shown once, stored as SHA-256, revocable; every call metered to the owner | `apps/api/app/routers/mcp.py` |
| API to providers | Platform keys in environment variables sourced from Key Vault, never returned. Personal keys encrypted at rest with Fernet (`PLAYGROUND_KEY_ENCRYPTION_KEY`), only the last four characters returned, resolved per call and never logged | `apps/api/app/keys.py`, `apps/api/app/llm.py` |
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
- CI runs gitleaks on every push (`.gitleaks.toml` allowlists only the test directories, whose keys are synthetic), plus `npm audit` and `pip-audit`.
- Personal tokens and the internal key never appear in logs or responses after creation.
- Personal provider keys are stored as Fernet ciphertext; the encryption key is required outside local environments and rotating it invalidates stored keys (people re-enter them). The judge, canaries and platform agents never use personal keys.

## What is out of scope for the pilot

SOC 2 evidence collection, Purview integration and Event Hub streaming were deliberately left for a later phase. The ledger already holds every event needed to feed them.

## Reporting

Report a suspected weakness to the repository owner with steps to reproduce. Do not open a public issue for an unpatched problem.


## Identity, permissions and governance, on any cloud

Sign-in is handled by Auth.js inside the web application, not by the hosting platform, so the identity provider is a deployment choice and not tied to Azure:

| Provider | Variables | Notes |
| --- | --- | --- |
| Microsoft Entra ID | `AUTH_MICROSOFT_ENTRA_ID_ID`, `AUTH_MICROSOFT_ENTRA_ID_SECRET`, `AUTH_MICROSOFT_ENTRA_ID_ISSUER` | The natural choice when the organisation runs on Microsoft 365 |
| Google Workspace | `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET` | Google-first organisations |
| Okta | `AUTH_OKTA_ID`, `AUTH_OKTA_SECRET`, `AUTH_OKTA_ISSUER` | Okta tenants |
| Any OpenID Connect provider | `AUTH_OIDC_ISSUER`, `AUTH_OIDC_ID`, `AUTH_OIDC_SECRET`, `AUTH_OIDC_NAME` | Ping, Auth0, Keycloak, ADFS and other OIDC servers; the name labels the sign-in button |

Several providers can be enabled at once; the sign-in page shows one button per provider. The Bicep template passes the Entra and OIDC variables through (`entra*`, `oidc*` parameters); the others can be added as Container App environment variables in the same way.

**Who may sign in.** `AUTH_ALLOWED_DOMAINS` (comma-separated e-mail domains) and `AUTH_ALLOWED_EMAILS` restrict single sign-on to the organisations and people you name; when both are empty, any account the provider authenticates is accepted, which is only right for a provider that already scopes to one organisation. `AUTH_ADMIN_EMAILS` names the people who become administrators on first sign-in; everyone else receives `AUTH_DEFAULT_ROLE` (explorer unless set) and, as a department, their e-mail domain until an administrator changes it on the Users page. The seeded pilot accounts switch themselves off as soon as a provider is configured, unless `ALLOW_DEV_LOGIN=true` keeps them alongside it for a demonstration.

**Permissions.** Four roles (admin, champion, builder, explorer) are the unit of permission today: each role has a model policy (which tiers and providers), a budget and a set of allowed tools and connectors, all editable by administrators on the Policies and Budgets pages, and every person's role can be changed on the Users page. Personal API tokens inherit the person's role. The next steps when a client needs more are, in order: department-level policies (the department already flows from the identity provider), group claims from the provider mapped to roles (so the identity team, not the playground, decides who is an administrator), and SCIM provisioning for joiners and leavers. None of these change the data model: roles, departments and policies are already rows the identity layer fills.

**Governance and security** do not depend on the identity provider either: the ledger, budgets, policies, the approval queue for connectors, the evaluation gates and the canary all key off the person's identity headers, which the web application derives from the session and the API trusts only together with the internal key. Signing out records a sign-out time so a session cannot be revived by a late response; the API is never exposed publicly; provider keys live in Key Vault and are only ever stored encrypted per person.
