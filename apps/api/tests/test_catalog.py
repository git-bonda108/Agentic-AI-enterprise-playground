from app.catalog_store import FAMILIES, load_entries, stats
from app.curator import curate, review


def test_catalog_has_every_family_and_enough_entries(client, headers):
    entries = load_entries()
    assert len(entries) >= 150
    fams = {e["family"] for e in entries}
    assert set(FAMILIES) == fams
    assert sum(1 for e in entries if e["family"] == "Domain") == 6
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids)), "duplicate catalog ids"


def test_curator_marks_at_least_sixty_green():
    rows = curate(write=False)
    green = [r for r in rows if r["status"] == "green"]
    assert len(green) >= 60, len(green)
    assert all(r["status"] in ("green", "red") for r in rows)


def test_curator_rejects_broken_entries():
    bad = {"id": "x", "name": "", "family": "Role", "source": {"repo": "r", "path": "p", "license": "MIT", "url": "http://insecure", "title": "t"}, "summary": "short", "instructions": "tiny", "tools": [], "tags": [], "runnable": True, "tier": "Workhorse"}
    result = review(bad)
    assert result["status"] == "red" and result["reasons"]


def test_catalog_api_filters_and_detail(client, headers):
    body = client.get("/v1/catalog?family=Role", headers=headers).json()
    assert body["total"] >= 60 and all(e["family"] == "Role" for e in body["entries"])
    assert "instructions" not in body["entries"][0] and body["entries"][0]["instructions_preview"]
    search = client.get("/v1/catalog?q=security", headers=headers).json()
    assert search["total"] >= 1
    lowcode = client.get("/v1/catalog?family=Low-code", headers=headers).json()
    assert lowcode["total"] == 16
    cloud = client.get("/v1/catalog?family=Cloud&runnable=false", headers=headers).json()
    assert cloud["total"] >= 15
    detail = client.get(f"/v1/catalog/{body['entries'][0]['id']}", headers=headers).json()
    assert detail["instructions"] and detail["curation"]["status"] in ("green", "red", "unreviewed")
    assert client.get("/v1/catalog/nope", headers=headers).status_code == 404
    s = stats()
    assert s["total"] == client.get("/v1/catalog/stats", headers=headers).json()["total"]


def test_catalog_entry_runs_as_prompt_agent(client, headers):
    r = client.post("/v1/runs", headers=headers, json={"blueprint_id": "ecc-security-reviewer", "input": {"task": "Review this login handler for OWASP issues: it compares passwords with ==."}, "wait": True})
    assert r.status_code == 201, r.text
    run = r.json()
    assert run["status"] == "completed" and run["blueprint_name"] == "Security Reviewer"
    assert run["output"]["answer_md"] and run["cost_usd"] > 0
    assert [s["node"] for s in run["steps"]] == ["prepare", "respond", "check"]
    manifest = client.get("/v1/runs/" + run["id"], headers=headers).json()
    assert manifest["blueprint_id"] == "ecc-security-reviewer"
    m = client.get("/v1/blueprints/ecc-security-reviewer", headers=headers).json()
    assert m["graph"]["nodes"][1]["id"] == "respond"


def test_lowcode_template_uses_knowledge(client, headers):
    r = client.post("/v1/runs", headers=headers, json={"blueprint_id": "lowcode-company-policy", "input": {"task": "What approvals does a 30,000 USD purchase need?"}, "wait": True}).json()
    assert r["status"] == "completed"
    assert "POL-002" in r["output"]["knowledge"]
    assert "POL-002" in r["output"]["answer_md"]


def test_cloud_mirror_is_not_runnable_and_hub_hides_runner(client, headers):
    assert client.post("/v1/runs", headers=headers, json={"blueprint_id": "cloud-adk-deep-search", "input": {}}).status_code == 404
    assert client.post("/v1/runs", headers=headers, json={"blueprint_id": "prompt-agent", "input": {}}).status_code == 404
    hub = client.get("/v1/blueprints", headers=headers).json()["blueprints"]
    assert all(b["id"] != "prompt-agent" for b in hub) and len(hub) == 8  # six domain blueprints plus two platform agents
    admin = client.post("/v1/catalog/curate", headers=headers).json()
    assert admin["reviewed"] >= 150 and admin["green"] >= 60
