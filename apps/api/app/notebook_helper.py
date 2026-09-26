"""playground: call the Enterprise AI Playground from a notebook.

The same file runs in the browser (Pyodide, inside JupyterLite) and in the server sandbox. It has no dependencies
beyond the standard library. Every call is made under your own identity, so policies, budgets and the ledger apply
exactly as they do in the playground pages.

    import playground as pg
    pg.hello()
    print(pg.chat("Say hello in one line."))
    run = pg.run("doc-reconciliation", {"tolerance_pct": 2})
    pg.show(run)
"""

from __future__ import annotations

import json
import os
import sys
import time

__version__ = "1.1.0"

_BASE = (os.environ.get("PLAYGROUND_API_URL") or "/api/pg").rstrip("/")
_HEADERS = {"content-type": "application/json", "accept": "application/json"}
for _k in ("INTERNAL_KEY", "USER_ID", "USER_EMAIL", "USER_NAME", "USER_ROLE", "USER_DEPARTMENT"):
    if os.environ.get("PLAYGROUND_" + _k):
        _HEADERS["X-" + _k.replace("_", "-").title()] = os.environ["PLAYGROUND_" + _k]
_IN_BROWSER = sys.platform == "emscripten"

last: dict | None = None  # the most recent API response, for inspection


class PlaygroundError(RuntimeError):
    """Raised when the playground refuses or fails a call (policy, budget, missing key, provider error)."""


def _request(method: str, path: str, body: dict | None = None) -> dict:
    """One HTTP call. In the browser a synchronous XMLHttpRequest carries the page's own session cookie."""
    global last
    url = _BASE + path
    data = json.dumps(body) if body is not None else None
    if _IN_BROWSER:
        from js import XMLHttpRequest  # type: ignore

        xhr = XMLHttpRequest.new()
        xhr.open(method, url, False)
        for k, v in _HEADERS.items():
            xhr.setRequestHeader(k, v)
        xhr.send(data)
        status, text = int(xhr.status), str(xhr.responseText)
    else:
        import urllib.error
        import urllib.request

        req = urllib.request.Request(url, data=data.encode() if data else None, headers=_HEADERS, method=method)
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                status, text = resp.status, resp.read().decode()
        except urllib.error.HTTPError as exc:
            status, text = exc.code, exc.read().decode()
    try:
        payload = json.loads(text) if text else {}
    except json.JSONDecodeError:
        payload = {"detail": text[:500]}
    if status >= 400:
        detail = payload.get("detail") if isinstance(payload, dict) else None
        raise PlaygroundError(f"{method} {path} -> {status}: {detail or text[:300]}")
    last = payload if isinstance(payload, dict) else {"data": payload}
    return payload


def get(path: str) -> dict:
    """GET any playground endpoint, for example ``pg.get('/v1/models')``."""
    return _request("GET", path)


def post(path: str, body: dict | None = None) -> dict:
    """POST any playground endpoint, for example ``pg.post('/v1/runs', {...})``."""
    return _request("POST", path, body or {})


# ------------------------------------------------------------------ models and chat ------------------------------------------------------------------

def models(available_only: bool = True) -> list[dict]:
    """The model catalog with prices; by default only models you can use right now (your key or the platform key)."""
    rows = get("/v1/models")["models"]
    return [m for m in rows if m.get("available") and m.get("allowed", True)] if available_only else rows


def chat(prompt: str | None = None, model: str = "smart", system: str | None = None, messages: list[dict] | None = None, max_tokens: int = 800) -> str:
    """One governed completion. Returns the text; the full response (tokens, cost, model) is in ``pg.last``."""
    msgs = list(messages or [])
    if system:
        msgs.insert(0, {"role": "system", "content": system})
    if prompt:
        msgs.append({"role": "user", "content": prompt})
    if not msgs:
        raise ValueError("Give a prompt or messages")
    return post("/v1/chat/complete", {"model": model, "messages": msgs, "max_tokens": max_tokens}).get("text", "")


def compare(prompt: str, model_ids: list[str], **kwargs) -> dict[str, str]:
    """The same prompt across several models; returns model id -> text and prints the cost of each."""
    out = {}
    for mid in model_ids:
        out[mid] = chat(prompt, model=mid, **kwargs)
        print(f"{mid}: ${(last or {}).get('cost_usd', 0):.5f} · {(last or {}).get('latency_ms', 0)} ms")
    return out


# ------------------------------------------------------------------ blueprints and runs ------------------------------------------------------------------

FINISHED = ("completed", "failed", "waiting_review")


def blueprints() -> list[dict]:
    """Every runnable blueprint with its sample inputs."""
    return get("/v1/blueprints")["blueprints"]


def run(blueprint_id: str, input: dict | None = None, wait: bool = True, timeout: int = 600, quiet: bool = False) -> dict:
    """Start a blueprint run and, by default, wait until it completes, fails or pauses for human review."""
    started = post("/v1/runs", {"blueprint_id": blueprint_id, "input": input or {}})
    if not wait:
        return started
    deadline = time.time() + timeout
    seen = 0
    current = started
    while current.get("status") not in FINISHED:
        if time.time() > deadline:
            raise PlaygroundError(f"Run {current.get('id')} still {current.get('status')} after {timeout}s")
        time.sleep(1.5)
        current = get(f"/v1/runs/{current['id']}")
        if not quiet:
            for s in (current.get("steps") or [])[seen:]:
                print(f"  · {s.get('node')}: {str(s.get('summary', ''))[:140]}")
            seen = len(current.get("steps") or [])
    if not quiet:
        print(f"{current['status']} · ${float(current.get('cost_usd') or 0):.4f} · {current.get('tokens_in', 0)} in / {current.get('tokens_out', 0)} out")
    return current


def resume(run_id: str, decision: str = "approve", note: str = "", wait: bool = True) -> dict:
    """Answer a human-review gate (``approve`` or ``reject``) and continue the run."""
    return post(f"/v1/runs/{run_id}/resume?wait={'true' if wait else 'false'}", {"answer": {"decision": decision, "notes": note}})


def runs(limit: int = 10) -> list[dict]:
    """Your recent runs."""
    return get(f"/v1/runs?limit={limit}")["runs"]


def output(run_or_id: dict | str) -> dict:
    """The output document of a run."""
    current = get(f"/v1/runs/{run_or_id}") if isinstance(run_or_id, str) else run_or_id
    return current.get("output") or {}


def markdown_of(run_or_id: dict | str) -> str:
    """The main narrative of a run's output as Markdown (summary, answer, path or narrative), or pretty JSON."""
    out = output(run_or_id)
    for key in ("summary_md", "answer_md", "path_md", "narrative_md", "report_md", "post_md", "digest_md"):
        if out.get(key):
            return str(out[key])
    return "```json\n" + json.dumps(out, indent=2)[:4000] + "\n```"


def show(thing: dict | str) -> None:
    """Render Markdown in the notebook (falls back to print outside IPython). Accepts a run, a run id or Markdown text."""
    text = thing if isinstance(thing, str) and " " in thing else markdown_of(thing)
    try:
        from IPython.display import Markdown, display  # type: ignore

        display(Markdown(text))
    except Exception:  # noqa: BLE001  (no IPython in the sandbox)
        print(text)


# ------------------------------------------------------------------ data and knowledge ------------------------------------------------------------------

def datasets() -> list[dict]:
    """The mock datasets that ship with the playground, with row counts and a preview."""
    return get("/v1/data")["datasets"]


def dataset(name: str) -> list[dict] | dict:
    """All rows of one mock dataset (a list of dicts, or a dict of lists for keyed corpora)."""
    return get(f"/v1/data/{name}")["rows"]


def frame(name: str):
    """A pandas DataFrame of a mock dataset (pandas is available in the browser and the sandbox)."""
    import pandas as pd  # type: ignore

    rows = dataset(name)
    return pd.DataFrame(rows) if isinstance(rows, list) else pd.DataFrame([{"key": k, "items": v} for k, v in rows.items()])


def spaces() -> list[dict]:
    """Knowledge Spaces you can read."""
    return get("/v1/knowledge/spaces")["spaces"]


def search(space_id: str, query: str, k: int = 5) -> list[dict]:
    """Hybrid search in a Knowledge Space; returns the passages with scores."""
    return post(f"/v1/knowledge/spaces/{space_id}/search", {"query": query, "k": k}).get("hits", [])


def ask(space_id: str, question: str) -> dict:
    """A grounded answer from a Knowledge Space, run through the Knowledge Q&A blueprint."""
    return post(f"/v1/knowledge/spaces/{space_id}/ask", {"question": question})


# ------------------------------------------------------------------ usage ------------------------------------------------------------------

def usage(days: int = 7) -> dict:
    """Your spend, tokens and requests for the last ``days`` days."""
    return get(f"/v1/usage/summary?days={days}")


def hello() -> None:
    """Confirm the connection: where you run, what you can use, what you have spent today."""
    available = models()
    u = usage(1)
    where = "browser" if _IN_BROWSER else "sandbox"
    print(f"playground {__version__} · {where} · {len(available)} models available · ${float(u.get('spend_window_usd') or 0):.4f} spent today")
    if not available:
        print("No model is available yet: open the Keys drawer in the playground and add a provider key.")


# Backwards-compatible names used by notebooks generated before version 1.1.
async def playground_post(path: str, body: dict) -> dict:
    return post(path, body)


async def playground_get(path: str) -> dict:
    return get(path)
