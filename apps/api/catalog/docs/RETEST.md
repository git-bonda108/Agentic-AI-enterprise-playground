# Release verification

A page-by-page check of every item in the left pane, run on 2026-09-27 against a production build with a fresh database and the fake model provider, then repeated by hand in a browser against the local development servers with real providers. The automated pass is a Playwright test that stays in the suite (`apps/web/e2e/batch17.spec.ts`): it visits every navigation item, checks the page heading, checks that the How to button is present wherever a page guide exists, and fails on any browser console error or any API call that returns a server error.

## What "ok" means

| Check | How |
| --- | --- |
| Heading | The level-one heading matches the navigation title (the console greets the person instead) |
| How to | Pages with a guide show the How to button |
| Console | No browser console error and no page error, after network idle |
| API | No response from the playground API with a 5xx status while the page loads |
| Hand check | The page's main interaction was exercised in a browser with real providers |

## Results

| Item | Path | Automated | Hand check |
| --- | --- | --- | --- |
| Console | /home | ok | Live ledger numbers, hours tiles with deltas, sign-in as two different people |
| Documentation | /docs | ok | Search, guide render with table of contents and images, cross-guide links, page guides |
| Models | /discover/models | ok | Provider filter, table view, Try opens the playground with the model |
| Blueprints | /discover/blueprints | ok | Category tabs, detail with graph and review gates, Build it your way |
| Frameworks | /discover/frameworks | ok (after fix) | Project render, smoke test in the sandbox, live run through the gateway |
| Low-code studios | /discover/low-code | ok | Langflow, n8n and Copilot Studio artefacts download |
| Cloud platforms | /discover/clouds | ok | Platform switch, sign-in block, guide builder, markdown download, deploy script |
| MCP Marketplace | /discover/connectors | ok | Featured shelf, per-client configuration, test connection |
| Popular Git repos | /discover/repos | ok | Category filter, stars and licences, reference implementations |
| Skills | /discover/skills | ok | Search and attach to an agent |
| Playground | /build/playground | ok | Streaming reply, compare four models, code dialog |
| Agent Hub | /build/agents | ok | Blueprint run with review gate, wizard agent with a built-in tool |
| Notebooks | /build/notebooks | ok | Gallery notebook runs in the browser and in the sandbox |
| Knowledge | /build/knowledge | ok | Space creation, hybrid search, grounded answer |
| Datasets | /build/data | ok | Columns and preview, CSV download, trusted sources with loaders |
| Evals | /evaluate/evals | ok | Suite run with judge scores and gates |
| Canary | /evaluate/canary | ok | Drift thresholds and the pass streak |
| Runs | /operate/runs | ok | Run list, control room view, review inbox |
| Traces | /operate/traces | ok | Gateway calls grouped by trace id |
| Cost | /operate/cost | ok | Layer switch, drill-down chips, ledger rows, CSV export |
| Adoption | /operate/adoption | ok | Hours per feature, ROI matrix, editable assumptions |
| Showcase | /community/showcase | ok | Published agents and the writer agent |
| Challenges | /community/challenges | ok | Challenge judged by the evaluation engine |
| Leaderboard | /community/leaderboard | ok | Achievements and rankings |
| Users | /admin/users | ok | People, roles and departments |
| Policies | /admin/policies | ok | Role policy blocks a frontier model |
| Budgets | /admin/budgets | ok | A tiny personal cap blocks the next call and raises an alert |
| Settings | /admin/settings | ok | Platform key scope switch, personal tokens, MCP client setup |

## Defects found and fixed during the retest

- The Frameworks page read the browser's address during rendering to build the gateway snippet, so the server and the browser produced different text whenever the site was not on port 3000. In production this surfaced as a React hydration error on every visit. The origin is now read through a store with a server fallback, and the same pattern in the code dialog was corrected.
- An older test on the Cost page matched two tables once the ledger rows table was added; it now targets the cost table.
- Signing out while a background request was in flight could bring the session back: the auth middleware re-issued the rolling session cookie on every request it handled, including the topbar's alert polls through the API proxy, and a poll that finished after sign-out re-set the cookie. The next sign-in then hit the "already signed in" redirect instead of the sign-in action and the browser showed an error page. The middleware now leaves the API proxy alone (its route handler answers 401 on its own), so background polls never touch the session cookie. A second run showed link prefetches from the page being left could do the same, and page renders refresh the cookie too, so the session is now closed by design rather than by timing: signing out records a sign-out time in its own cookie, every session carries the time it was issued, and the middleware, the app layout and the API proxy treat any session issued before the last sign-out as signed out and drop its cookie. A late response can no longer revive a session.

## Second pass, 2026-09-27, by hand with real providers

Every item was exercised again in a browser against the development servers with real provider keys, signed in as an administrator and as an explorer. Findings and what changed:

- **Notebooks.** JupyterLite restores the documents of the previous visit, so opening a second notebook left the earlier one open as a stale tab with its outputs cleared and no document active. That stale tab is what looked like greyed-out, dead code; the requested notebook itself ran every cell, including real model calls and a reconciliation run. The runtime is now loaded with its workspace reset, every other document is closed before the requested notebook opens, and the Run all button targets the requested notebook.
- **Agent Hub and Runs.** Timestamps were formatted with the machine's locale, so the server and the browser could disagree and the Agent Hub raised a hydration error whenever they did. Every server-rendered date, time and count now goes through one deterministic formatter (day, month name, year and UTC time).
- **Models.** The free NVIDIA developer endpoint showed a price of $0, which reads as a missing figure; it now reads "Free".
- **Admin pages as an explorer** show the "Admin role required" gate rather than the pages, which is the intended behaviour; as an administrator all four pages render and edit.
- Everything else behaved as the table above records: Playground reply and usage chip, blueprint runs and the review inbox, Knowledge Space search, Datasets downloads, Evals suites and Canary schedules, Traces, Cost drill-down, Adoption, Showcase, Challenges, Leaderboard, and every Discover page's filters, tabs, downloads and per-client configuration.

## How to rerun

```bash
cd apps/web && npx playwright test e2e/batch17.spec.ts
```

The test prints a `RETEST` block with one line per navigation item. The full suite (`npx playwright test`) builds the web application, starts the API with a fresh database and runs every specification in the project.
