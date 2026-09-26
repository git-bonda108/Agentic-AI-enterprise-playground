"""Notebook faces: generate .ipynb documents (blueprint MVPs, a getting-started gallery, runs, conversations) and execute them.

Every generated notebook starts with the same bootstrap cell that imports the ``playground`` helper module, so the
first cell works in the browser runtime and in the server sandbox alike. Whole notebooks can be executed cell by cell
in the sandbox, which is how the test suite proves that every MVP runs end to end on the mock data.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from app.config import settings

HELPER_PATH = Path(__file__).with_name("notebook_helper.py")
HELPER = HELPER_PATH.read_text()

BOOTSTRAP = '''# Playground helper: the same module in the browser and in the server sandbox.
try:
    import playground as pg
except ImportError:  # browser without the bundled file: fetch it from the API under your own session
    import sys, types
    from pyodide.http import open_url
    pg = types.ModuleType("playground"); exec(open_url("/api/pg/v1/notebooks/playground.py").read(), pg.__dict__); sys.modules["playground"] = pg
import json
pg.hello()'''

AUTHOR_REPOS = "https://github.com/git-bonda108"


def _cell(kind: str, source: str) -> dict:
    cell = {"cell_type": kind, "metadata": {}, "source": source}
    if kind == "code":
        cell.update({"execution_count": None, "outputs": []})
    return cell


def _notebook(cells: list[dict], title: str, **meta) -> dict:
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"name": "python", "display_name": "Python (Pyodide)", "language": "python"}, "language_info": {"name": "python"}, "playground": {"title": title, **meta}},
        "cells": cells,
    }


def _next_steps(manifest: dict | None = None, extra: list[str] | None = None) -> dict:
    lines = ["## Next steps", ""]
    if manifest:
        bid = manifest["id"]
        lines += [
            f"- **Customise**: change `payload` above, or open the [Agent Hub](/build/agents) to run *{manifest['name']}* with a review gate.",
            f"- **Take the code with you**: the same blueprint as an [OpenAI Agents SDK, LangGraph, CrewAI, Agent Framework or ADK project](/discover/frameworks?blueprint={bid}).",
            f"- **Deploy**: [cloud deploy scripts](/discover/clouds?blueprint={bid}) for Azure AI Foundry, Anthropic Managed Agents, AWS AgentCore and Google Agent Engine.",
            f"- **Measure**: build an [evaluation suite](/evaluate/evals?blueprint={bid}) from this run and schedule a canary.",
        ]
        for label, url in (manifest.get("links") or {}).items():
            if str(url).startswith("http"):
                lines.append(f"- **{label.title()}**: {url}")
    lines += extra or []
    lines += [f"- **Reference implementations**: [{AUTHOR_REPOS.replace('https://', '')}]({AUTHOR_REPOS}) hosts public repositories that build these patterns for real; read them, rate them in the [Showcase](/community/showcase) and borrow what fits."]
    return _cell("markdown", "\n".join(lines))


# ------------------------------------------------------------------ blueprint MVPs ------------------------------------------------------------------

CATEGORY = {"knowledge-qa": "Gen AI", "data-analyst": "Agentic AI", "doc-reconciliation": "Agentic AI", "sage-lens": "Agentic AI", "learning-path": "Agentic AI", "review-panel": "Agentic AI"}
LEVEL = {"knowledge-qa": "Starter", "data-analyst": "Starter", "sage-lens": "Intermediate", "learning-path": "Intermediate", "review-panel": "Intermediate", "doc-reconciliation": "Advanced"}


def notebook_for_blueprint(manifest: dict) -> dict:
    """A minimal viable notebook: meet the data, run the blueprint on it, read the trace and the output, then customise."""
    samples = manifest.get("samples") or [{"name": "Default", "input": {}}]
    sample = samples[0]["input"]
    datasets = manifest.get("datasets") or []
    steps = [n.get("label") or n.get("id") for n in (manifest.get("graph") or {}).get("nodes", [])]
    policy = ", ".join(f"{k} on {v}" for k, v in (manifest.get("tiers") or {}).items())
    cells = [
        _cell("markdown", f"# {manifest['name']}\n\n{manifest['description']}\n\n**Pattern:** {manifest['pattern']}  \n**Steps:** {' → '.join(str(s) for s in steps) if steps else 'single model call'}  \n**Model policy:** {policy}\n\nEverything below runs under your identity: policy, budget and the ledger apply exactly as in the playground pages. Run the cells top to bottom (Run all works too)."),
        _cell("code", BOOTSTRAP),
    ]
    if datasets:
        cells += [
            _cell("markdown", "## 1. Meet the data\n\nThe blueprint ships with mock data so the MVP runs without any setup. Swap in your own data later."),
            _cell("code", "for d in pg.datasets():\n    if d['id'] in " + json.dumps(datasets) + ":\n        print(f\"{d['id']:<18} {d['rows']:>4} rows · {d['title']} · {d['source']}\")\nrows = pg.dataset(" + json.dumps(datasets[0]) + ")\nprint()\nprint(json.dumps(rows[:2] if isinstance(rows, list) else list(rows)[:5], indent=2)[:1200])"),
        ]
    other = "\n".join(f"# {s['name']}: {json.dumps(s['input'])}" for s in samples[1:4])
    n = 2 if datasets else 1
    cells += [
        _cell("markdown", f"## {n}. Run the MVP\n\nOne call starts a checkpointed run and prints the trace as each step finishes. Edit `payload` and run again."),
        _cell("code", f"payload = {json.dumps(sample, indent=2)}\n{other}\nrun = pg.run({json.dumps(manifest['id'])}, payload)"),
        _cell("markdown", f"## {n + 1}. Read the output\n\nThe narrative is Markdown; the structured output is a dictionary you can post-process."),
        _cell("code", "pg.show(run)\nout = pg.output(run)\nprint('\\nkeys:', sorted(out.keys()))"),
    ]
    if manifest.get("review_gates"):
        cells += [
            _cell("markdown", f"## {n + 2}. Human review\n\nThis blueprint pauses for review at: {', '.join(manifest['review_gates'])}. When a run is `waiting_review`, approve or reject it from here or from the Agent Hub."),
            _cell("code", "if run['status'] == 'waiting_review':\n    run = pg.resume(run['id'], decision='approve', note='Approved from the notebook')\n    pg.show(run)\nelse:\n    print('No review was needed for this input:', run['status'])"),
        ]
    cells += [
        _cell("markdown", "## Customise\n\nAsk a model to explain or extend the result. `smart` picks the cheapest capable tier; name a model id to pin one (`pg.models()` lists what you can use)."),
        _cell("code", "print(pg.chat('In three bullets, what did this run conclude and what should a reviewer check first? ' + pg.markdown_of(run)[:2500], model='smart'))\nprint(f\"cost ${pg.last['cost_usd']:.5f} on {pg.last['model']}\")"),
        _next_steps(manifest),
    ]
    return _notebook(cells, manifest["name"], kind="blueprint", blueprint_id=manifest["id"], category=CATEGORY.get(manifest["id"], "Agentic AI"), level=LEVEL.get(manifest["id"], "Intermediate"))


def notebook_for_run(run: dict, manifest: dict) -> dict:
    cells = [
        _cell("markdown", f"# Run of {manifest['name']}\n\nStatus: {run['status']} · cost ${run['cost_usd']:.4f} · {run['tokens_in']} in / {run['tokens_out']} out."),
        _cell("code", BOOTSTRAP),
        _cell("markdown", "## The input that was used"),
        _cell("code", f"payload = {json.dumps(run['input'], indent=2)}"),
        _cell("markdown", "## The recorded output"),
        _cell("code", f"output = {json.dumps(run.get('output') or {}, indent=2)}\npg.show(pg.markdown_of({{'output': output}}))"),
        _cell("markdown", "## Re-run with a change\nTweak `payload` above, then run this cell."),
        _cell("code", f"again = pg.run({json.dumps(run['blueprint_id'])}, payload)\npg.show(again)"),
        _next_steps(manifest),
    ]
    return _notebook(cells, f"Run {run['id'][:8]}", kind="run", blueprint_id=run["blueprint_id"])


def notebook_for_conversation(conv: dict) -> dict:
    history = [{"role": m["role"], "content": m["content"]} for m in conv.get("messages", [])]
    cells = [
        _cell("markdown", f"# {conv['title']}\n\nModel: {conv['model']}. The conversation history is loaded below; continue it with a new question."),
        _cell("code", BOOTSTRAP),
        _cell("code", f"history = {json.dumps(history, indent=2)}\nfor m in history:\n    print(m['role'].upper() + ':', m['content'][:300], '\\n')"),
        _cell("markdown", "## Continue the conversation"),
        _cell("code", f"question = 'Summarize what we discussed in three bullets.'\nprint(pg.chat(question, model={json.dumps(conv['model'])}, messages=history))\nprint('cost', pg.last.get('cost_usd'))"),
    ]
    return _notebook(cells, conv["title"], kind="conversation")


def notebook_blank() -> dict:
    return _notebook([
        _cell("markdown", "# Scratch notebook\n\nRuns in your browser or in the server sandbox. `pg` calls any playground endpoint under your own identity and budget; `help(pg)` lists everything."),
        _cell("code", BOOTSTRAP),
        _cell("code", "for m in pg.models():\n    print(f\"{m['id']:<22} {m['tier']:<9} ${m['input_per_m']}/{m['output_per_m']} per 1M\")"),
        _cell("code", "print(pg.chat('Say hello in one line.'))\nprint(pg.last['model'], pg.last['cost_usd'])"),
    ], "Scratch notebook", kind="blank", category="Gen AI", level="Starter")


# ------------------------------------------------------------------ getting-started gallery ------------------------------------------------------------------

def _nb_hello() -> dict:
    return _notebook([
        _cell("markdown", "# Hello, playground\n\nTen minutes from zero to a governed model call: see what you can use, ask a model, read the cost. This notebook is the first thing to run after adding a provider key from the Keys drawer."),
        _cell("code", BOOTSTRAP),
        _cell("markdown", "## Which models can I use?\n\n`pg.models()` shows models that are both allowed by your role policy and backed by a key (yours or the platform's)."),
        _cell("code", "for m in pg.models():\n    print(f\"{m['id']:<22} {m['provider']:<13} {m['tier']:<9} ${m['input_per_m']:>6} in / ${m['output_per_m']:>6} out per 1M · key: {m.get('key_source')}\")"),
        _cell("markdown", "## Ask a model\n\n`smart` lets the router pick the cheapest capable tier for the prompt and records the saving against a premium baseline."),
        _cell("code", "answer = pg.chat('Explain in two sentences what an agentic workflow is, for a finance analyst.', model='smart')\nprint(answer)\nprint(f\"\\n{pg.last['model']} · {pg.last['tokens_in']} in / {pg.last['tokens_out']} out · ${pg.last['cost_usd']:.5f}\")"),
        _cell("markdown", "## What did that cost?\n\nEvery call lands in the ledger. The same numbers drive the Cost page and your budget."),
        _cell("code", "u = pg.usage(days=1)\nprint(f\"today: {u['requests']} requests · {u['tokens_window']} tokens · ${u['spend_window_usd']:.4f}\")\nfor f in u['by_feature']:\n    print(f\"  {f['feature']:<10} ${f['cost_usd']:.4f}\")"),
        _next_steps(None, ["- **Compare models** on the same prompt in the next notebook, or open the [Playground](/build/playground) for a chat UI with the same governance."]),
    ], "Hello, playground", kind="gallery", slug="hello-playground", category="Gen AI", level="Starter")


def _nb_compare() -> dict:
    return _notebook([
        _cell("markdown", "# Compare models on one prompt\n\nThe cheapest model that meets the bar wins. This notebook runs one prompt across up to three models you can use and shows text, latency and cost side by side, then asks a model to judge the answers against a rubric."),
        _cell("code", BOOTSTRAP),
        _cell("code", "prompt = 'A supplier invoice is 3% higher than its purchase order. List the three checks an accounts-payable analyst should do before approving it.'\ncandidates = [m['id'] for m in pg.models()][:3]\nprint('comparing', candidates)\nanswers = pg.compare(prompt, candidates, max_tokens=300)"),
        _cell("code", "for mid, text in answers.items():\n    print('=' * 80)\n    print(mid)\n    print(text[:800])"),
        _cell("markdown", "## Judge the answers\n\nA model grades each answer 1 to 5 on completeness and clarity. This is the seed of an evaluation suite; the Evaluate page turns it into gates and canaries."),
        _cell("code", "rubric = 'Score each answer from 1 (poor) to 5 (excellent) on completeness and clarity. Reply as a short table: model | score | one-line reason.'\ngraded = pg.chat(rubric + '\\n\\n' + '\\n\\n'.join(f'[{k}]\\n{v[:600]}' for k, v in answers.items()), model='smart', max_tokens=300)\nprint(graded)"),
        _next_steps(None, ["- **Make it a suite**: [Evaluate](/evaluate/evals) builds golden cases from runs and schedules nightly canaries.", "- **Route automatically**: try the [Smart routing preview](/build/playground?model=smart) to see which tier a prompt lands on."]),
    ], "Compare models", kind="gallery", slug="compare-models", category="Gen AI", level="Starter")


def _nb_pandas() -> dict:
    return _notebook([
        _cell("markdown", "# Data analysis with pandas and a narrator model\n\nDeterministic code does the arithmetic; the model writes the narrative. This is the pattern behind the Data analyst blueprint, shown in plain pandas so you can adapt it to your own tables."),
        _cell("code", BOOTSTRAP),
        _cell("code", "import pandas as pd\ndf = pg.frame('sales')\ndf['date'] = pd.to_datetime(df['date'])\ndf['revenue'] = df['revenue'].astype(float)\ndf['units'] = df['units'].astype(int)\nprint(df.shape)\nprint(df.head())"),
        _cell("code", "by_region = df.groupby('region')['revenue'].sum().sort_values(ascending=False)\nmonthly = df.set_index('date').resample('MS')['revenue'].sum()\nprint(by_region.round(0))\nprint()\nprint(monthly.round(0).tail(6))"),
        _cell("markdown", "## Let the model narrate the numbers\n\nThe model never computes; it explains figures the code produced. That keeps the story auditable."),
        _cell("code", "facts = 'Revenue by region: ' + repr(by_region.round(0).to_dict()) + '. Last six months: ' + repr({str(k.date()): v for k, v in monthly.round(0).tail(6).to_dict().items()})\nprint(pg.chat('Write a four-sentence executive summary from these facts. Do not invent numbers. ' + facts, model='smart', max_tokens=250))"),
        _cell("markdown", "## Install a package\n\nIn the server sandbox, `%pip install <package>` installs into your own environment and stays for later runs. In the browser, `%pip` installs pure-Python wheels through micropip."),
        _cell("code", "%pip install tabulate\nfrom tabulate import tabulate\nprint(tabulate(by_region.reset_index().values.tolist(), headers=['region', 'revenue'], floatfmt='.0f'))"),
        _next_steps(None, ["- **Run it as an agent**: the [Data analyst blueprint](/build/notebooks?blueprint=data-analyst) plans, writes and executes the analysis for any question.", "- **Bring your own data**: upload a CSV to a [Knowledge Space](/build/knowledge) or point the sandbox at your files."]),
    ], "Data analysis with pandas", kind="gallery", slug="data-with-pandas", category="Gen AI", level="Intermediate")


def _nb_knowledge() -> dict:
    return _notebook([
        _cell("markdown", "# Retrieval Q&A over a Knowledge Space\n\nCreate a space, load the policies dataset into it, search it and ask grounded questions. Answers cite the passages they used; ungrounded answers are flagged."),
        _cell("code", BOOTSTRAP),
        _cell("code", "spaces = [s for s in pg.spaces() if s['name'].startswith('Notebook policies')]\nspace = spaces[0] if spaces else pg.post('/v1/knowledge/spaces', {'name': 'Notebook policies', 'description': 'Created from the Knowledge Q&A notebook'})\nsid = space['id']\nif not spaces:\n    doc = pg.post(f'/v1/knowledge/spaces/{sid}/documents/dataset', {'dataset': 'policies'})\n    print('loaded', doc.get('chunk_count'), 'chunks')\nprint('space', sid, space['name'])"),
        _cell("markdown", "## Search\n\nHybrid retrieval: dense vectors plus BM25, fused by reciprocal rank."),
        _cell("code", "for h in pg.search(sid, 'hotel limit per night', k=3):\n    print(f\"{h.get('score', 0):.3f}  {h.get('title', '')}: {h.get('text', '')[:140]}\")"),
        _cell("markdown", "## Ask\n\n`ask` runs the Knowledge Q&A blueprint: retrieve, answer with citations, verify grounding."),
        _cell("code", "res = pg.ask(sid, 'What is the hotel limit per night when travelling?')\nprint(json.dumps(res, indent=2)[:1500])"),
        _next_steps(None, ["- **Add your own documents**: PDF, Word, Markdown, URLs or a repository map, from the [Knowledge page](/build/knowledge).", "- **Turn it into an agent**: the no-code [Agent wizard](/build/agents) attaches a space to any agent."]),
    ], "Retrieval Q&A over a Knowledge Space", kind="gallery", slug="knowledge-qa-space", category="Gen AI", level="Intermediate")


def _nb_review() -> dict:
    return _notebook([
        _cell("markdown", "# An agent that pauses for human review\n\nDocument reconciliation matches invoices to purchase orders and contracts, then stops at a review gate when it is not sure. This notebook runs it, inspects the exception, and resumes it with a decision, the same flow the Agent Hub's review inbox uses."),
        _cell("code", BOOTSTRAP),
        _cell("code", "run = pg.run('doc-reconciliation', {'invoice_numbers': ['INV-9002', 'INV-9005', 'INV-9012']})\nprint(run['status'])"),
        _cell("markdown", "## What is the agent asking a human to decide?"),
        _cell("code", "review = run.get('review') or {}\nprint(json.dumps(review, indent=2)[:2000] if review else 'No review requested for this input.')"),
        _cell("markdown", "## Decide and resume\n\nThe checkpoint survives restarts: a reviewer can come back tomorrow and the run continues from exactly here."),
        _cell("code", "if run['status'] == 'waiting_review':\n    run = pg.resume(run['id'], 'approve', 'Reviewed in the notebook: amounts within tolerance')\npg.show(run)"),
        _cell("markdown", "## Where every dollar went"),
        _cell("code", "for s in run['steps']:\n    print(f\"{s['node']:<18} {str(s.get('summary', ''))[:100]}\")\nprint(f\"total ${run['cost_usd']:.4f}\")"),
        _next_steps({"id": "doc-reconciliation", "name": "Document reconciliation", "links": {"origin": "https://github.com/git-bonda108/agentic-invoice-processing"}}),
    ], "An agent that pauses for human review", kind="gallery", slug="agent-with-review", category="Agentic AI", level="Advanced")


def _nb_tool_loop() -> dict:
    return _notebook([
        _cell("markdown", "# Build your own tool-using agent in 40 lines\n\nThe model chooses an action as JSON; your Python runs the tool deterministically; the loop repeats until the model says it is done. No framework, so every moving part is visible. The framework flavors on the Frameworks page produce the same loop in OpenAI Agents SDK, LangGraph, CrewAI, Agent Framework and ADK."),
        _cell("code", BOOTSTRAP),
        _cell("code", "invoices = {r['invoice_number']: r for r in pg.dataset('invoices')}\npos = {r['po_number']: r for r in pg.dataset('purchase_orders')}\n\ndef lookup_invoice(number):\n    r = invoices.get(number)\n    return {k: r[k] for k in ('invoice_number', 'vendor', 'po_number', 'amount', 'currency')} if r else {'error': 'unknown invoice'}\n\ndef lookup_po(number):\n    r = pos.get(number)\n    return {k: r[k] for k in ('po_number', 'vendor', 'amount', 'currency')} if r else {'error': 'unknown PO'}\n\nTOOLS = {'lookup_invoice': lookup_invoice, 'lookup_po': lookup_po}\nprint(len(invoices), 'invoices,', len(pos), 'purchase orders')"),
        _cell("code", "SYSTEM = ('You are a reconciliation agent. Tools: lookup_invoice(number), lookup_po(number). '\n          'Reply ONLY with JSON: {\"action\": \"<tool name>\", \"args\": {...}} to call a tool, or {\"action\": \"final\", \"answer\": \"...\"} when done.')\n\ndef agent(task, max_steps=4):\n    history = [{'role': 'user', 'content': task}]\n    for step in range(max_steps):\n        reply = pg.chat(system=SYSTEM, messages=history, max_tokens=200)\n        try:\n            decision = json.loads(reply[reply.find('{'): reply.rfind('}') + 1])\n        except (ValueError, TypeError):\n            return f'(model did not return JSON on step {step + 1}; raw reply: {reply[:200]})'\n        if decision.get('action') == 'final':\n            return decision.get('answer')\n        fn = TOOLS.get(decision.get('action'))\n        result = fn(**decision.get('args', {})) if fn else {'error': 'unknown tool'}\n        print(f'step {step + 1}: {decision.get(\"action\")}({decision.get(\"args\")}) -> {result}')\n        history += [{'role': 'assistant', 'content': reply}, {'role': 'user', 'content': 'Tool result: ' + json.dumps(result)}]\n    return 'stopped after max steps'\n\nprint(agent('Does invoice INV-9002 match its purchase order amount? Look both up and answer in one sentence.'))"),
        _cell("markdown", "## Why this matters\n\nThe arithmetic and the lookups are code, so they are testable and free. The model only decides what to do next. The Blueprints, evaluation gates and hardening levels in the playground are this loop with checkpoints, metering and review added around it."),
        _next_steps(None, ["- **Same loop, five frameworks**: [Frameworks](/discover/frameworks?blueprint=doc-reconciliation).", "- **Give it real tools**: approved [MCP connectors](/discover/connectors) can be called from any agent."]),
    ], "Build your own tool-using agent", kind="gallery", slug="tool-loop", category="Agentic AI", level="Advanced")


GALLERY_BUILDERS = {"hello-playground": _nb_hello, "compare-models": _nb_compare, "data-with-pandas": _nb_pandas, "knowledge-qa-space": _nb_knowledge, "agent-with-review": _nb_review, "tool-loop": _nb_tool_loop}
GALLERY_META = [
    {"slug": "hello-playground", "title": "Hello, playground", "blurb": "Models you can use, one governed call, what it cost.", "category": "Gen AI", "level": "Starter", "minutes": 5, "tags": ["chat", "cost"]},
    {"slug": "compare-models", "title": "Compare models", "blurb": "One prompt across three models with a judge and costs.", "category": "Gen AI", "level": "Starter", "minutes": 8, "tags": ["compare", "evaluation"]},
    {"slug": "data-with-pandas", "title": "Data analysis with pandas", "blurb": "Code does the maths, a model narrates; install a package.", "category": "Gen AI", "level": "Intermediate", "minutes": 10, "tags": ["pandas", "pip"]},
    {"slug": "knowledge-qa-space", "title": "Retrieval Q&A over a Knowledge Space", "blurb": "Create a space, load data, search, ask with citations.", "category": "Gen AI", "level": "Intermediate", "minutes": 10, "tags": ["RAG", "knowledge"]},
    {"slug": "agent-with-review", "title": "An agent that pauses for human review", "blurb": "Run reconciliation, inspect the exception, resume.", "category": "Agentic AI", "level": "Advanced", "minutes": 12, "tags": ["human review", "checkpoints"]},
    {"slug": "tool-loop", "title": "Build your own tool-using agent", "blurb": "A 40-line tool loop with deterministic tools.", "category": "Agentic AI", "level": "Advanced", "minutes": 15, "tags": ["tools", "agent loop"]},
]


def notebook_for_gallery(slug: str) -> dict | None:
    builder = GALLERY_BUILDERS.get(slug)
    return builder() if builder else None


def gallery(manifests: list[dict]) -> list[dict]:
    """Getting-started notebooks first, then one MVP per domain blueprint."""
    out = [{**m, "path": f"/v1/notebooks/gallery/{m['slug']}.ipynb", "kind": "gallery"} for m in GALLERY_META]
    for m in manifests:
        out.append({
            "slug": m["id"], "title": m["name"], "blurb": m.get("summary") or m["description"][:120], "category": CATEGORY.get(m["id"], "Agentic AI"), "level": LEVEL.get(m["id"], "Intermediate"),
            "minutes": 10, "tags": [m.get("pattern", "")] + list(m.get("datasets") or []), "path": f"/v1/notebooks/blueprint/{m['id']}.ipynb", "kind": "blueprint", "blueprint_id": m["id"],
        })
    return out


# ------------------------------------------------------------------ compute options ------------------------------------------------------------------

def compute_options(notebook_path: str, file_name: str) -> list[dict]:
    """Where a notebook can run. External targets need the notebook at a public URL; locally they get download instructions."""
    base = settings.self_url.rstrip("/")
    public = base.startswith("https://") and "localhost" not in base and "127.0.0.1" not in base
    raw_url = f"{base}{notebook_path}" if public else None
    brev = f"https://brev.nvidia.com/environment/new?instance=A10G:g5.xlarge&name={file_name.replace('.ipynb', '')}&file={raw_url}&python=3.12&cuda=12.6" if raw_url else "https://brev.nvidia.com/launchables"
    return [
        {"id": "browser", "name": "In browser", "cost": "Free", "blurb": "Pyodide runtime in this tab. No install, pure-Python packages via micropip. Best for reading and light work.", "action": "open"},
        {"id": "sandbox", "name": "Playground sandbox", "cost": "Included", "blurb": "Isolated Python on the playground with your identity. Real packages with pip, results metered to you. Azure dynamic sessions in production.", "action": "run"},
        {"id": "brev", "name": "NVIDIA Brev", "cost": "GPU by the hour", "blurb": "A GPU launchable with this notebook preloaded. Sign in with your NVIDIA account; pick the GPU on the next screen.", "action": "link", "url": brev, "download_first": not public, "docs": "https://docs.nvidia.com/brev/latest/launchables-create.html"},
        {"id": "colab", "name": "Google Colab", "cost": "Free tier, Pro for GPUs", "blurb": "Download the notebook and upload it to Colab, or push it to GitHub and open it from there.", "action": "link", "url": "https://colab.research.google.com/#create=true", "download_first": True, "docs": "https://colab.research.google.com/notebooks/intro.ipynb"},
        {"id": "codespaces", "name": "GitHub Codespaces", "cost": "Free hours, then per core-hour", "blurb": "Commit the notebook to a repository and open a codespace with the Python image.", "action": "link", "url": "https://github.com/codespaces/new", "download_first": True, "docs": "https://docs.github.com/en/codespaces/developing-in-a-codespace/getting-started-with-github-codespaces-for-machine-learning"},
    ]


# ------------------------------------------------------------------ execution ------------------------------------------------------------------

SANDBOX_ROOT = Path(settings.checkpoint_path).parent / "sandboxes" if settings.checkpoint_path else Path(__file__).resolve().parents[1] / "data" / "sandboxes"
PACKAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-\[\]]*(?:[=<>!~]=?[A-Za-z0-9_.*+!-]+)?$")


def _venv_dir(user_id: str) -> Path:
    return SANDBOX_ROOT / re.sub(r"[^A-Za-z0-9_-]", "_", user_id) / "venv"


def sandbox_python(user_id: str) -> str:
    """The interpreter for a person's sandbox: their own environment once they installed a package, else the API's."""
    candidate = _venv_dir(user_id) / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(candidate) if candidate.exists() else sys.executable


def ensure_sandbox_env(user_id: str) -> str:
    """Create the person's sandbox environment (with pip, and the API's packages visible) and return its interpreter."""
    venv = _venv_dir(user_id)
    if not venv.exists():
        venv.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, capture_output=True, timeout=180)
        # The API itself runs in a virtual environment, so --system-site-packages would not expose its packages
        # (pandas, numpy, httpx...). A .pth file appends them after the person's own installs, which take precedence.
        import sysconfig

        site = next(venv.glob("lib/python*/site-packages"), None) or next(venv.glob("Lib/site-packages"), None)
        if site is not None:
            (site / "playground_base.pth").write_text(sysconfig.get_paths()["purelib"] + "\n")
    return sandbox_python(user_id)


def pip_install(user_id: str, packages: list[str], timeout: int = 240) -> dict:
    """Install packages into the person's sandbox environment (created on first use, with the API's packages visible)."""
    bad = [p for p in packages if not PACKAGE_RE.match(p)]
    if bad:
        return {"ok": False, "stdout": "", "stderr": f"Refused package specifiers: {', '.join(bad)}", "ms": 0}
    started = time.perf_counter()
    python = ensure_sandbox_env(user_id)
    proc = subprocess.run([python, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", *packages], capture_output=True, text=True, timeout=timeout, check=False)
    return {"ok": proc.returncode == 0, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:], "ms": int((time.perf_counter() - started) * 1000), "python": python}


RUNNER = r'''
import contextlib, io, json, subprocess, sys, traceback
cells = json.load(open("cells.json"))
ns = {"__name__": "__main__"}
def _magic(line):
    parts = line.split()
    if parts[:2] in (["%pip", "install"], ["!pip", "install"]):
        proc = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", *parts[2:]], capture_output=True, text=True, timeout=240)
        return (proc.stdout + proc.stderr).strip() or ("installed " + " ".join(parts[2:]))
    return "(skipped: " + line + ")"
for i, src in enumerate(cells):
    buf, err = io.StringIO(), None
    code = []
    for line in src.splitlines():
        if line.lstrip().startswith(("%", "!")):
            buf.write(_magic(line.strip()) + "\n")
        else:
            code.append(line)
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            exec(compile("\n".join(code), f"<cell {i + 1}>", "exec"), ns)
        except SystemExit:
            pass
        except BaseException:
            err = traceback.format_exc()
    sys.__stdout__.write("@@CELL@@" + json.dumps({"cell": i, "stdout": buf.getvalue()[-20000:], "error": err}) + "\n")
    sys.__stdout__.flush()
    if err:
        break
'''


def _limited_env(tmp: str, env: dict[str, str]) -> dict[str, str]:
    return {"PATH": os.environ.get("PATH", ""), "HOME": tmp, "PYTHONIOENCODING": "utf-8", "MPLBACKEND": "Agg", **env}


def execute_notebook(cells: list[str], env: dict[str, str], user_id: str, timeout: int = 300) -> dict:
    """Run code cells in order in one sandbox process, sharing state like a kernel. Stops at the first error."""
    started = time.perf_counter()
    if any(re.search(r"^\s*[%!]pip\s+install", c, re.MULTILINE) for c in cells):
        ensure_sandbox_env(user_id)  # the runner installs with its own interpreter, which must carry pip
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "cells.json").write_text(json.dumps(cells))
        Path(tmp, "playground.py").write_text(HELPER)
        Path(tmp, "runner.py").write_text(RUNNER)
        try:
            proc = subprocess.run([sandbox_python(user_id), "-s", "runner.py"], cwd=tmp, env=_limited_env(tmp, env), capture_output=True, text=True, timeout=timeout, check=False)
            stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode(errors="replace")
            stderr, code = f"Timed out after {timeout}s", 124
    results = []
    for line in stdout.splitlines():
        if line.startswith("@@CELL@@"):
            try:
                results.append(json.loads(line[len("@@CELL@@"):]))
            except json.JSONDecodeError:
                continue
    ok = code == 0 and all(r.get("error") is None for r in results) and len(results) == len(cells)
    return {"backend": "local", "ok": ok, "cells": results, "stderr": stderr[-4000:], "exit_code": code, "ms": int((time.perf_counter() - started) * 1000)}


def execute_local(code: str, env: dict[str, str], timeout: int = 20, user_id: str = "anonymous") -> dict:
    """Development sandbox: one snippet in an isolated Python subprocess with a hard timeout and the helper on the path.

    This is not a security boundary; production uses Azure Container Apps dynamic sessions (Hyper-V isolated).
    """
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "cell.py").write_text(code)
        Path(tmp, "playground.py").write_text(HELPER)
        try:
            proc = subprocess.run([sandbox_python(user_id), "-s", "cell.py"], cwd=tmp, env=_limited_env(tmp, env), capture_output=True, text=True, timeout=timeout, check=False)
            return {"backend": "local", "stdout": proc.stdout[-20000:], "stderr": proc.stderr[-20000:], "exit_code": proc.returncode, "ms": int((time.perf_counter() - started) * 1000)}
        except subprocess.TimeoutExpired as exc:
            return {"backend": "local", "stdout": (exc.stdout or "")[-20000:] if isinstance(exc.stdout, str) else "", "stderr": f"Timed out after {timeout}s", "exit_code": 124, "ms": timeout * 1000}


def execute_aca(code: str, session_id: str) -> dict:
    """Azure Container Apps dynamic sessions code interpreter. Requires PLAYGROUND_SANDBOX_ENDPOINT and Azure credentials."""
    import httpx
    from azure.identity import DefaultAzureCredential  # type: ignore

    token = DefaultAzureCredential().get_token("https://dynamicsessions.io/.default").token
    url = f"{settings.sandbox_endpoint.rstrip('/')}/code/execute?api-version=2024-02-02-preview&identifier={session_id}"
    started = time.perf_counter()
    r = httpx.post(url, headers={"Authorization": f"Bearer {token}"}, json={"properties": {"codeInputType": "inline", "executionType": "synchronous", "code": code}}, timeout=90)
    r.raise_for_status()
    props = r.json().get("properties", {})
    return {"backend": "aca-sessions", "stdout": str(props.get("stdout", "")) + str(props.get("result", "") or ""), "stderr": str(props.get("stderr", "")), "exit_code": 0 if not props.get("stderr") else 1, "ms": int((time.perf_counter() - started) * 1000)}


def execute(code: str, env: dict[str, str], session_id: str, user_id: str = "anonymous") -> dict:
    if settings.sandbox_endpoint:
        return execute_aca(code, session_id)
    return execute_local(code, env, user_id=user_id)
