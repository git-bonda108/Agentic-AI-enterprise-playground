"""Batch 11: the playground helper, the notebook gallery, whole-notebook execution in the sandbox, pip installs, compute options."""

import json
import socket
import threading
import time

import pytest
import uvicorn
from conftest import HEADERS

from app import notebook_helper as helper
from app.config import settings
from app.main import app
from app.notebooks import GALLERY_META, compute_options


@pytest.fixture(scope="module")
def live_server(client):
    """A real HTTP server on a free port so sandbox subprocesses can call the API with the shared in-memory database."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="off")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    previous = settings.self_url
    settings.self_url = f"http://127.0.0.1:{port}"
    yield settings.self_url
    settings.self_url = previous
    server.should_exit = True
    thread.join(timeout=5)


def test_helper_module_is_served_and_talks_to_the_api(client, headers, monkeypatch):
    src = client.get("/v1/notebooks/playground.py", headers=headers)
    assert src.status_code == 200 and "def run(" in src.text and "def chat(" in src.text

    # route the helper's transport through the test client so every wrapper is exercised in-process
    def transport(method, path, body=None):
        r = client.request(method, path, headers=headers, json=body)
        if r.status_code >= 400:
            raise helper.PlaygroundError(f"{method} {path} -> {r.status_code}: {r.text[:200]}")
        helper.last = r.json()
        return helper.last

    monkeypatch.setattr(helper, "_request", transport)
    assert any(m["id"] == "gpt-5-nano" for m in helper.models())
    text = helper.chat("Say hello in one line.")
    assert text and helper.last["cost_usd"] >= 0
    rows = helper.dataset("invoices")
    assert isinstance(rows, list) and rows[0]["invoice_number"].startswith("INV-")
    assert any(d["id"] == "sales" for d in helper.datasets())
    run = helper.run("knowledge-qa", {"question": "What is the hotel limit per night?"}, quiet=True)
    assert run["status"] in ("completed", "waiting_review") and helper.markdown_of(run)
    assert client.get("/v1/data/nope", headers=headers).status_code == 404


def test_gallery_lists_getting_started_and_blueprint_mvps(client, headers):
    body = client.get("/v1/notebooks/gallery", headers=headers).json()["notebooks"]
    slugs = [n["slug"] for n in body]
    assert [m["slug"] for m in GALLERY_META] == slugs[: len(GALLERY_META)]
    assert {"doc-reconciliation", "sage-lens", "knowledge-qa", "data-analyst"} <= set(slugs)
    assert all(n["category"] in ("Gen AI", "Agentic AI") and n["level"] in ("Starter", "Intermediate", "Advanced") for n in body)
    for n in body:
        nb = client.get(n["path"], headers=headers)
        assert nb.status_code == 200, n["path"]
        cells = nb.json()["cells"]
        assert cells[1]["source"].startswith("# Playground helper"), n["path"]
        assert "Next steps" in cells[-1]["source"] and "git-bonda108" in cells[-1]["source"]
    assert client.get("/v1/notebooks/gallery/nope.ipynb", headers=headers).status_code == 404


@pytest.mark.parametrize("path", ["/v1/notebooks/blank.ipynb", *[f"/v1/notebooks/gallery/{m['slug']}.ipynb" for m in GALLERY_META], "/v1/notebooks/blueprint/doc-reconciliation.ipynb", "/v1/notebooks/blueprint/knowledge-qa.ipynb", "/v1/notebooks/blueprint/data-analyst.ipynb", "/v1/notebooks/blueprint/sage-lens.ipynb", "/v1/notebooks/blueprint/learning-path.ipynb", "/v1/notebooks/blueprint/review-panel.ipynb"])
def test_every_mvp_notebook_executes_end_to_end_in_the_sandbox(client, headers, live_server, path):
    """The promise of Batch 11: every shipped notebook runs top to bottom on the mock data with no configuration."""
    res = client.post("/v1/notebooks/execute", headers=headers, json={"path": path, "timeout": 300}).json()
    failed = [c for c in res["cells"] if c.get("error")]
    assert res["ok"], f"{path}: exit {res['exit_code']} · {res['stderr'][-500:]} · {json.dumps(failed)[:1500]}"
    first = res["cells"][0]["stdout"]
    assert "playground 1.1.0" in first and "sandbox" in first, first
    assert len(res["cells"]) == sum(1 for c in client.get(path, headers=headers).json()["cells"] if c["cell_type"] == "code")


def test_execute_reports_the_failing_cell_and_keeps_state_between_cells(client, headers, live_server):
    res = client.post("/v1/notebooks/execute", headers=headers, json={"cells": ["x = 21", "print(x * 2)", "raise ValueError('boom')", "print('never')"]}).json()
    assert res["ok"] is False and len(res["cells"]) == 3
    assert res["cells"][1]["stdout"].strip() == "42" and "boom" in res["cells"][2]["error"]
    assert client.post("/v1/notebooks/execute", headers=headers, json={}).status_code == 400
    assert client.post("/v1/notebooks/execute", headers=headers, json={"path": "/etc/passwd"}).status_code == 400


def test_pip_install_and_magics_in_the_sandbox(client, headers, live_server):
    refused = client.post("/v1/sandbox/pip", headers=headers, json={"packages": ["--index-url=evil"]}).json()
    assert refused["ok"] is False and "Refused" in refused["stderr"]
    res = client.post("/v1/notebooks/execute", headers=headers, json={"cells": ["%pip install tabulate", "import tabulate\nprint('has tabulate', bool(tabulate.__version__))", "!ls\nprint('after magic')"]}).json()
    assert res["ok"], json.dumps(res)[:1500]
    assert "has tabulate True" in res["cells"][1]["stdout"] and "skipped: !ls" in res["cells"][2]["stdout"]


def test_compute_options_and_heartbeat(client, headers, monkeypatch):
    opts = client.get("/v1/notebooks/compute?path=/v1/notebooks/gallery/hello-playground.ipynb", headers=headers).json()["options"]
    ids = [o["id"] for o in opts]
    assert ids == ["browser", "sandbox", "brev", "colab", "codespaces"]
    brev = next(o for o in opts if o["id"] == "brev")
    assert brev["download_first"] is True and brev["url"].startswith("https://brev.nvidia.com")
    monkeypatch.setattr(settings, "self_url", "https://playground.example.com/api/pg")
    public = compute_options("/v1/notebooks/gallery/hello-playground.ipynb", "hello-playground.ipynb")
    assert "file=https://playground.example.com/api/pg/v1/notebooks/gallery/hello-playground.ipynb" in public[2]["url"] and public[2]["download_first"] is False
    assert client.get("/v1/notebooks/compute?path=/etc/passwd", headers=headers).status_code == 400
    assert client.post("/v1/notebooks/heartbeat", headers=headers, json={"path": "/v1/notebooks/blank.ipynb", "mode": "browser"}).status_code == 202
    rows = client.get("/v1/usage/breakdown?days=1&by=model", headers=headers).json()["rows"]
    assert any(r["key"] == "editor-browser" for r in rows)
    assert HEADERS["X-User-Id"] == "u1"
