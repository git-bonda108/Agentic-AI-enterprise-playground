"""Notebook faces: generate .ipynb documents from runs, conversations and blueprints, and execute code in a sandbox."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time

from app.config import settings

HELPER = '''import json, os

BASE = os.environ.get("PLAYGROUND_API_URL", "") + ("" if os.environ.get("PLAYGROUND_API_URL") else "/api/pg")
_HEADERS = {"content-type": "application/json"}
for _k in ("INTERNAL_KEY", "USER_ID", "USER_EMAIL", "USER_NAME", "USER_ROLE", "USER_DEPARTMENT"):
    if os.environ.get("PLAYGROUND_" + _k):
        _HEADERS["X-" + _k.replace("_", "-").title()] = os.environ["PLAYGROUND_" + _k]

async def playground_post(path, body):
    """POST to the playground API. Works in the browser (Pyodide) and in the server sandbox."""
    try:
        from pyodide.http import pyfetch
        r = await pyfetch(BASE + path, method="POST", headers=_HEADERS, body=json.dumps(body))
        return await r.json()
    except ImportError:
        import urllib.request
        req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers=_HEADERS, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.load(resp)

async def playground_get(path):
    try:
        from pyodide.http import pyfetch
        r = await pyfetch(BASE + path, headers=_HEADERS)
        return await r.json()
    except ImportError:
        import urllib.request
        req = urllib.request.Request(BASE + path, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)

print("playground helpers ready; base =", BASE or "same origin")'''


def _cell(kind: str, source: str) -> dict:
    cell = {"cell_type": kind, "metadata": {}, "source": source}
    if kind == "code":
        cell.update({"execution_count": None, "outputs": []})
    return cell


def _notebook(cells: list[dict], title: str) -> dict:
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"name": "python", "display_name": "Python (Pyodide)", "language": "python"}, "language_info": {"name": "python"}, "playground": {"title": title}},
        "cells": cells,
    }


def notebook_for_blueprint(manifest: dict) -> dict:
    sample = (manifest.get("samples") or [{"input": {}}])[0]["input"]
    cells = [
        _cell("markdown", f"# {manifest['name']}\n\n{manifest['description']}\n\nPattern: {manifest['pattern']}. Every call below is metered to you like the playground."),
        _cell("code", HELPER),
        _cell("markdown", "## Run the blueprint on mock data\nEdit `payload` and re-run the cell. `wait` returns when the run finishes or pauses for review."),
        _cell("code", f"payload = {json.dumps(sample, indent=2)}\nrun = await playground_post('/v1/runs', {{'blueprint_id': '{manifest['id']}', 'input': payload, 'wait': True}})\nprint(run['status'], '·', f\"${{run['cost_usd']:.4f}}\")\nfor s in run['steps']:\n    print('-', s['node'], ':', s['summary'])"),
        _cell("markdown", "## Inspect the output"),
        _cell("code", "out = run.get('output') or {}\nmd = out.get('summary_md') or out.get('answer_md') or out.get('path_md') or out.get('narrative_md')\nprint(md or json.dumps(out, indent=2)[:3000])"),
        _cell("markdown", "## Ask a model directly\nSame governance: policy, budget and the ledger apply."),
        _cell("code", "resp = await playground_post('/v1/chat/complete', {'model': 'smart', 'messages': [{'role': 'user', 'content': 'In two sentences, what does this blueprint do? ' + json.dumps(out)[:1500]}]})\nprint(resp.get('text') or resp)"),
    ]
    return _notebook(cells, manifest["name"])


def notebook_for_run(run: dict, manifest: dict) -> dict:
    cells = [
        _cell("markdown", f"# Run of {manifest['name']}\n\nStatus: {run['status']} · cost ${run['cost_usd']:.4f} · {run['tokens_in']} in / {run['tokens_out']} out."),
        _cell("code", HELPER),
        _cell("markdown", "## The input that was used"),
        _cell("code", f"payload = {json.dumps(run['input'], indent=2)}"),
        _cell("markdown", "## The recorded output"),
        _cell("code", f"output = {json.dumps(run.get('output') or {}, indent=2)}\nprint(json.dumps(output, indent=2)[:3000])"),
        _cell("markdown", "## Re-run with a change\nTweak `payload` above, then run this cell."),
        _cell("code", f"again = await playground_post('/v1/runs', {{'blueprint_id': '{run['blueprint_id']}', 'input': payload, 'wait': True}})\nprint(again['status'], '·', f\"${{again['cost_usd']:.4f}}\")"),
    ]
    return _notebook(cells, f"Run {run['id'][:8]}")


def notebook_for_conversation(conv: dict) -> dict:
    history = [{"role": m["role"], "content": m["content"]} for m in conv.get("messages", [])]
    cells = [
        _cell("markdown", f"# {conv['title']}\n\nModel: {conv['model']}. The conversation history is loaded below; continue it with a new question."),
        _cell("code", HELPER),
        _cell("code", f"history = {json.dumps(history, indent=2)}\nfor m in history:\n    print(m['role'].upper() + ':', m['content'][:300], '\\n')"),
        _cell("markdown", "## Continue the conversation"),
        _cell("code", f"question = 'Summarize what we discussed in three bullets.'\nresp = await playground_post('/v1/chat/complete', {{'model': '{conv['model']}', 'messages': history + [{{'role': 'user', 'content': question}}]}})\nprint(resp.get('text') or resp)\nprint('cost', resp.get('cost_usd'))"),
    ]
    return _notebook(cells, conv["title"])


def notebook_blank() -> dict:
    return _notebook([
        _cell("markdown", "# Scratch notebook\n\nRuns in your browser. Use `playground_post` and `playground_get` to call any playground endpoint under your own identity and budget."),
        _cell("code", HELPER),
        _cell("code", "models = await playground_get('/v1/models')\nprint([m['id'] for m in models['models'] if m['available']])"),
        _cell("code", "resp = await playground_post('/v1/chat/complete', {'model': 'smart', 'messages': [{'role': 'user', 'content': 'Say hello in one line.'}]})\nprint(resp.get('text') or resp)"),
    ], "Scratch notebook")


def execute_local(code: str, env: dict[str, str], timeout: int = 20) -> dict:
    """Development sandbox: an isolated Python subprocess in a temp directory with a hard timeout.

    This is not a security boundary; production uses Azure Container Apps dynamic sessions (Hyper-V isolated).
    """
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "cell.py")
        with open(path, "w") as f:
            f.write(code)
        limited_env = {"PATH": os.environ.get("PATH", ""), "HOME": tmp, "PYTHONIOENCODING": "utf-8", **env}
        try:
            proc = subprocess.run([sys.executable, "-I", path], cwd=tmp, env=limited_env, capture_output=True, text=True, timeout=timeout, check=False)
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


def execute(code: str, env: dict[str, str], session_id: str) -> dict:
    if settings.sandbox_endpoint:
        return execute_aca(code, session_id)
    return execute_local(code, env)
