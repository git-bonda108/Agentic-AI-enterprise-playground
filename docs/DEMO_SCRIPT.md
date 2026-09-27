# Demo and test script

A step-by-step walk through every capability, in the order a client demo flows. Each step says what to click and what you should see. About 40 minutes end to end; the first six steps cover the RFP's mandatory demo items.

## Before you start

```bash
git clone https://github.com/git-bonda108/Agentic-AI-enterprise-playground.git
cd Agentic-AI-enterprise-playground
npm run start:local
```

The launcher installs what is missing, seeds a demo tenant (ten people, a month of usage, runs, knowledge, evaluations, a canary, showcase posts and a judged challenge), starts the API on port 8000 and the web app on port 3000, and opens the browser. Add provider keys to `.env` for live models; without them run `npm run start:offline`, which answers with a deterministic provider at no cost.

Sign in as **Satya Bonda** (administrator, password `playground`). The other nine seeded people sign in the same way; use Priya Raman (champion) or Carlos Mendes (explorer) to show different policies.

## 1. Console (2 minutes)

Home → Console. Expect organisation credits, spend this month against the cap, seven-day token volume, cache reuse, and a live ledger listing the last calls with model, tokens and cost.

## 2. Playground and multi-model access (5 minutes)

Build → Playground.

1. Leave **Smart** selected, type "Summarise the travel policy for a new joiner", send. Expect a streamed reply with the routed model, tier and cost in the footer.
2. Click **Compare**, add Claude Sonnet 5 and GPT-5.6 Terra, send the same prompt. Expect side-by-side answers, each with its own cost.
3. Click **View code**. Expect the same request in Python, TypeScript, curl, the Anthropic SDK and the OpenAI SDK.
4. Save the conversation with a tag; it appears in the sidebar.

Discover → Models. Expect fifteen models with tier, provider, prices per million tokens, capabilities and availability.

## 3. Security and governance (4 minutes)

Admin → Policies: limit the explorer role to Economy and Workhorse tiers. Sign in as Carlos Mendes in a private window and try Claude Opus 5.5: expect a policy refusal.

Admin → Budgets: set Carlos's personal cap to one dollar. Expect alerts in the bell at 50, 80 and 100 percent, and a hard stop at 100.

Admin → Settings: providers configured, runtime, and the personal token panel for MCP clients.

## 4. Cost management (3 minutes)

Operate → Cost. Expect KPIs and a breakdown you can switch between day, department, user, feature, model, provider and conversation. Every number reconciles to the same ledger rows. The Smart routing savings figure shows what the router avoided against a premium baseline.

## 5. Agents and human review (6 minutes)

Build → Agent Hub.

1. Run **Document reconciliation** with the "Escalate over tolerance" sample. Expect the animated graph, steps with timing, and a pause at the review gate listing the escalated invoices.
2. Choose a decision and submit. Expect the run to complete with a controller-ready summary.
3. Click the **Control room** tab. Expect the three governed lanes (deterministic, agentic, governed), the record under review, the reasoning trace, the exception ledger and the outcome tiles.
4. Run **Sage Lens** with "Give me an overview". Expect a clarifying question; answer it and get a brief with sources.

Discover → Blueprints. Expect 175 entries across six families with four faces on every card: Run, Notebook, Code, Deploy.

## 6. Success stories and community (3 minutes)

Community → Showcase: seeded posts with outcomes, likes and comments. Click **Publish**, pick one of your runs, click **Draft with the writer agent**; expect a title, summary, outcome and tags written by the platform agent. Edit and publish.

Community → Challenges: a closed challenge with judged standings and a winner. Community → Leaderboard: achievements with progress, people and departments.

## 7. Notebooks, code and clouds (4 minutes)

Build → Notebooks: open a blueprint as a notebook; expect it inside the in-browser runtime. Switch to Server sandbox and run `print(6 * 7)`.

Discover → Frameworks: pick CrewAI; expect a runnable project with README, sample input, requirements and an offline smoke test; download the zip.

Discover → Cloud platforms: pick AWS AgentCore; expect Open portal, the CLI sign-in commands, the pricing unit, and a numbered guide that changes with the framework and model.

## 8. Wizard, knowledge, skills, connectors (6 minutes)

Build → Knowledge: open the seeded space, search "hotel per night", then Ask "What is the hotel limit per night?" Expect a grounded answer with a verified citation. Map the repository and open the Graph tab.

Build → Agent Hub → Create your own agent: fill the six fields, attach the Knowledge Space, a skill and the playground connector, run it. Expect a tools step in the run.

Discover → Connectors: search "Enterprise AI Playground", Test connection; expect the five tools. Discover → Skills: browse 338 packs.

## 9. Evaluate and canary (4 minutes)

Evaluate → Evals: open the Knowledge Q&A golden set, Run suite. Expect per-case checks, judge scores, the gate verdict and the hardening ladder lighting up. Build a suite with the guided wizard.

Evaluate → Canary: Run now on a suite. Expect the drift chart and a stable verdict.

## 10. Adoption and the digest (2 minutes)

Operate → Adoption: hours per feature, cost per outcome, the ROI matrix by department with editable assumptions. Click **Generate digest**; expect a narrative and three recommendations written by the adoption digest agent.

## 11. The playground as an MCP server (2 minutes)

Admin → Settings → create a personal token, paste the configuration into Claude Desktop or Cursor. Ask the assistant to list your models or run a blueprint. Expect the call to appear in the ledger under your name.

## Automated checks

```bash
cd apps/api && uv run pytest -q
```

```bash
npm run typecheck && npm run lint && npm run test:e2e
```
