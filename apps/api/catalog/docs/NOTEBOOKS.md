# Notebooks

Every blueprint in the playground runs end to end in a notebook on mock data, with nothing to configure beyond a provider key. This guide covers the gallery, the `playground` helper, the places a notebook can run, package installs and how notebook time is measured.

## The gallery

Build → Notebooks opens the gallery. Notebooks are grouped the way the blueprints are:

| Group | What it teaches | Notebooks |
| --- | --- | --- |
| Gen AI | Single-model patterns: chat, comparison, retrieval, analysis | Hello playground · Compare models · Data analysis with pandas · Retrieval Q&A over a Knowledge Space · Knowledge Q&A blueprint |
| Agentic AI | Multi-step agents with tools, checkpoints and human review | An agent that pauses for human review · Build your own tool-using agent · Document reconciliation · Sage Lens · Learning path · Review panel · Data analyst |

Each card carries a level (Starter, Intermediate, Advanced), the minutes it takes, and two actions: **Open** loads it in the browser runtime; **Run in sandbox** executes every cell on the server and shows the outputs.

Every notebook has the same shape: a title cell that states the pattern and the model policy, the bootstrap cell, numbered sections (meet the data, run the MVP, read the output, human review where the blueprint has a gate, customise), and a **Next steps** cell with the framework flavors, deploy scripts, evaluation suite, the provider's official documentation and reference implementations.

## The `playground` helper

The bootstrap cell imports one module, `playground`, aliased as `pg`. It is the same file in the browser and in the sandbox and needs nothing beyond the standard library. Calls run under your identity, so policies, budgets and the ledger apply.

| Call | What it does |
| --- | --- |
| `pg.hello()` | Where you run, how many models you can use, what you spent today |
| `pg.models()` | Models that are allowed for your role and backed by a key (yours or the platform's) |
| `pg.chat(prompt, model="smart", system=None, messages=None)` | One governed completion; the full response is in `pg.last` |
| `pg.compare(prompt, [model ids])` | The same prompt across models with cost and latency per model |
| `pg.run(blueprint_id, input)` | Start a run and wait, printing each step; returns the run |
| `pg.resume(run_id, "approve" or "reject", note)` | Answer a human-review gate |
| `pg.show(run)` / `pg.markdown_of(run)` / `pg.output(run)` | Render or extract a run's output |
| `pg.datasets()` / `pg.dataset(name)` / `pg.frame(name)` | The mock datasets, as rows or as a pandas DataFrame |
| `pg.spaces()` / `pg.search(space_id, query)` / `pg.ask(space_id, question)` | Knowledge Spaces |
| `pg.usage(days)` | Your spend, tokens and requests |
| `pg.get(path)` / `pg.post(path, body)` | Any endpoint in [docs/API.md](API.md) |

In the browser the helper is bundled in the runtime's file drive; if it is missing it fetches itself from `/v1/notebooks/playground.py` under your session. In the sandbox it is placed next to the notebook.

## Where a notebook runs

| Compute | Cost | When to use it |
| --- | --- | --- |
| In browser | Free | Reading, light work, pure-Python packages via micropip. Nothing leaves your tab except the API calls. |
| Playground sandbox | Included | Runs the whole notebook top to bottom in an isolated Python process with your identity; real packages; outputs shown per cell. Locally this is a subprocess; in Azure it is a Container Apps dynamic session. |
| NVIDIA Brev | GPU by the hour | A launchable with the notebook preloaded. The deep link works once the playground has a public address; locally, download the notebook and upload it. |
| Google Colab | Free tier, Pro for GPUs | Download and upload, or push the notebook to GitHub and open it from there. |
| GitHub Codespaces | Free hours, then per core-hour | Commit the notebook to a repository and open a codespace with the Python image. |

**More compute** in the notebook toolbar shows the external options with their documentation links.

## Packages

In the sandbox, `%pip install <package>` inside a cell, or the **Install packages** box, installs into your own environment (created on first use, with the platform's packages visible). Installed packages stay for later runs. Package specifiers are validated; flags and URLs are refused. In the browser, `%pip install` uses micropip and works for pure-Python wheels.

## What counts as notebook time

The adoption page counts hours per feature from the ledger. A notebook records a zero-cost heartbeat every three minutes while it is open and visible, and every model call, run and sandbox execution records its own row, so notebook hours are measured rather than estimated.

## Verification

`apps/api/tests/test_notebooks.py` starts a real HTTP server and executes every gallery and blueprint notebook in the sandbox; a notebook that fails any cell fails the build. The Playwright suite runs one from the gallery in the browser.
