import io
import json
import py_compile
import subprocess
import tempfile
import zipfile

import pytest

from app.agents.golden import GOLDEN
from app.deploy import CLOUDS
from app.flavors import FRAMEWORKS


@pytest.mark.parametrize("framework", list(FRAMEWORKS.keys()))
def test_every_blueprint_renders_a_compiling_project(client, headers, framework):
    for blueprint_id in GOLDEN:
        body = client.get(f"/v1/blueprints/{blueprint_id}/flavor/{framework}", headers=headers).json()
        files = body["files"]
        assert {"agent.py", "README.md", "sample_input.json", "requirements.txt", "test_smoke.py"} <= set(files)
        for name, content in files.items():
            if name.endswith(".py"):
                with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
                    f.write(content)
                py_compile.compile(f.name, doraise=True)
        json.loads(files["sample_input.json"])
        # the generated offline smoke test passes against its own project
        with tempfile.TemporaryDirectory() as d:
            for name, content in files.items():
                with open(f"{d}/{name}", "w") as fh:
                    fh.write(content)
            out = subprocess.run(["python3", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--import-mode=importlib", d], capture_output=True, text=True, timeout=120, check=False)
            assert out.returncode == 0, out.stdout[-800:]


def test_flavor_zip_downloads(client, headers):
    r = client.get("/v1/blueprints/sage-lens/flavor/langgraph/download", headers=headers)
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert "sage-lens-langgraph/agent.py" in names
    assert client.get("/v1/blueprints/sage-lens/flavor/nope", headers=headers).status_code == 404
    assert client.get("/v1/frameworks", headers=headers).json()["frameworks"][0]["install"]


@pytest.mark.parametrize("cloud", list(CLOUDS.keys()))
def test_deploy_scripts_pass_a_shell_dry_run(client, headers, cloud):
    for blueprint_id in ("doc-reconciliation", "ecc-security-reviewer", "lowcode-it-helpdesk"):
        body = client.get(f"/v1/blueprints/{blueprint_id}/deploy/{cloud}", headers=headers).json()
        assert body["pricing"] and body["docs"].startswith("https://")
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
            f.write(body["script"])
        assert subprocess.run(["bash", "-n", f.name], capture_output=True, check=False).returncode == 0, cloud
    assert client.get("/v1/clouds", headers=headers).json()["clouds"]


def test_notebooks_are_valid_ipynb(client, headers):
    for path in ("/v1/notebooks/blank.ipynb", "/v1/notebooks/blueprint/doc-reconciliation.ipynb", "/v1/notebooks/blueprint/ecc-planner.ipynb"):
        r = client.get(path, headers=headers)
        assert r.status_code == 200 and "ipynb" in r.headers["content-type"]
        nb = r.json()
        assert nb["nbformat"] == 4 and nb["cells"] and any(c["cell_type"] == "code" and "playground_post" in c["source"] for c in nb["cells"])
    run = client.post("/v1/runs", headers=headers, json={"blueprint_id": "knowledge-qa", "input": {"question": "hotel limit"}, "wait": True}).json()
    nb = client.get(f"/v1/notebooks/run/{run['id']}.ipynb", headers=headers).json()
    assert "hotel limit" in json.dumps(nb)
    conv = client.post("/v1/conversations", headers=headers, json={"title": "Notebook seed chat", "model": "claude-sonnet-5"}).json()
    nb2 = client.get(f"/v1/notebooks/conversation/{conv['id']}.ipynb", headers=headers).json()
    assert "Notebook seed chat" in json.dumps(nb2)


def test_sandbox_executes_python_locally(client, headers):
    r = client.post("/v1/sandbox/execute", headers=headers, json={"code": "import os\nprint(1 + 1)\nprint(os.environ.get('PLAYGROUND_USER_ID'))"}).json()
    assert r["backend"] == "local" and r["exit_code"] == 0
    assert r["stdout"].splitlines() == ["2", "u1"]
    bad = client.post("/v1/sandbox/execute", headers=headers, json={"code": "raise ValueError('boom')"}).json()
    assert bad["exit_code"] != 0 and "boom" in bad["stderr"]
    summary = client.get("/v1/usage/breakdown?days=1&by=feature", headers=headers).json()
    assert any(r["key"] == "notebook" for r in summary["rows"])


def test_chat_complete_is_governed(client, headers):
    r = client.post("/v1/chat/complete", headers=headers, json={"model": "smart", "messages": [{"role": "user", "content": "Translate 'hello' to French."}]}).json()
    assert r["text"] and r["routed"] is True and r["cost_usd"] > 0
    explorer = {**headers, "X-User-Id": "u5", "X-User-Email": "carlos@playground.local", "X-User-Role": "explorer"}
    assert client.post("/v1/chat/complete", headers=explorer, json={"model": "claude-fable-5-1", "messages": [{"role": "user", "content": "hi"}]}).status_code == 403


def test_custom_agent_wizard_roundtrip(client, headers):
    body = {"name": "Expense helper", "description": "Answers expense questions for our team.", "instructions": "You answer expense and travel questions using the policies provided and cite the policy id.", "knowledge": ["policies"], "starters": ["What is the hotel limit?", "Can I claim taxi rides?"], "published": True}
    created = client.post("/v1/custom-agents", headers=headers, json=body).json()
    assert created["id"].startswith("custom-")
    listing = client.get("/v1/catalog?family=Low-code", headers=headers).json()
    assert any(e["id"] == created["id"] and e["curation"]["status"] == "green" for e in listing["entries"])
    run = client.post("/v1/runs", headers=headers, json={"blueprint_id": created["id"], "input": {"task": "What is the hotel limit per night?"}, "wait": True}).json()
    assert run["status"] == "completed" and "POL-001" in run["output"]["knowledge"]
    export = client.get(f"/v1/custom-agents/{created['id']}/export/declarative-agent", headers=headers)
    assert export.status_code == 200
    manifest = export.json()
    assert manifest["version"] == "v1.5" and manifest["instructions"] == body["instructions"] and len(manifest["conversation_starters"]) == 2
    other = {**headers, "X-User-Id": "u9", "X-User-Email": "ravi@playground.local", "X-User-Role": "builder"}
    assert any(a["id"] == created["id"] for a in client.get("/v1/custom-agents", headers=other).json()["agents"])  # published
    assert client.delete(f"/v1/custom-agents/{created['id']}", headers=other).status_code == 404
    assert client.delete(f"/v1/custom-agents/{created['id']}", headers=headers).status_code == 204
