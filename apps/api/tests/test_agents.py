"""Blueprint harness: every golden case runs green on mock data with the fake provider; interrupts survive a runtime restart."""

import pytest

from app.agents import runtime
from app.agents.core import REGISTRY
from app.agents.golden import GOLDEN
from app.agents.registry import all_blueprints  # noqa: F401  (populate registry)


def _run(client, headers, blueprint_id, payload, resume=None):
    r = client.post("/v1/runs", headers=headers, json={"blueprint_id": blueprint_id, "input": payload, "wait": True})
    assert r.status_code == 201, r.text
    run = r.json()
    if run["status"] == "waiting_review":
        assert resume is not None, f"{blueprint_id} asked for review with no resume answer: {run['review']}"
        r = client.post(f"/v1/runs/{run['id']}/resume?wait=true", headers=headers, json={"answer": resume})
        assert r.status_code == 200, r.text
        run = client.get(f"/v1/runs/{run['id']}", headers=headers).json()
    return run


def _check(run, expect):
    out = run["output"] or {}
    assert run["status"] == expect.get("status", "completed"), run.get("error")
    if "review_required" in expect:
        assert any(s["kind"] == "human" and "Human" in s["summary"] or "Clarified" in s["summary"] for s in run["steps"]) == expect["review_required"], [s["summary"] for s in run["steps"]]
    for code in expect.get("anomaly_codes", []):
        assert code in {a["code"] for a in out.get("anomalies", [])}, code
    if "escalated_min" in expect:
        assert len(out.get("escalated", [])) >= expect["escalated_min"]
    if "anomalies_max" in expect:
        assert len(out.get("anomalies", [])) <= expect["anomalies_max"]
    if "sources_min" in expect:
        assert len(out.get("sources", [])) >= expect["sources_min"]
    if "attempts_max" in expect:
        assert out.get("attempts", 0) <= expect["attempts_max"]
    for k, v in expect.get("output_eq", {}).items():
        assert out.get(k) == v, (k, out.get(k))
    for k in expect.get("output_has", []):
        assert k in out, k
    if "levels" in expect:
        assert len(out.get("path", {})) == expect["levels"]
    if "reference_contains" in expect:
        urls = " ".join(r["url"] for refs in out.get("references", {}).values() for r in refs)
        assert expect["reference_contains"] in urls, urls
    if "blockers_min" in expect:
        assert len(out.get("blockers", [])) >= expect["blockers_min"], out.get("critics")
    if "table_rows" in expect:
        assert len(out.get("table", [])) == expect["table_rows"]
    if expect.get("chart"):
        assert out.get("chart") and out["chart"]["data"]
    if "top_retrieved" in expect:
        assert out["retrieved"][0]["id"] == expect["top_retrieved"], out["retrieved"]


def test_all_blueprints_registered(client, headers):
    body = client.get("/v1/blueprints", headers=headers).json()
    ids = {b["id"] for b in body["blueprints"]}
    assert ids == set(GOLDEN.keys()) == {k for k, bp in REGISTRY.items() if bp.family != "Runtime"}
    assert all(len(cases) == 10 for cases in GOLDEN.values())


@pytest.mark.parametrize("blueprint_id", list(GOLDEN.keys()))
def test_golden_cases(client, headers, blueprint_id):
    for i, case in enumerate(GOLDEN[blueprint_id]):
        run = _run(client, headers, blueprint_id, case["input"], case.get("resume"))
        try:
            _check(run, case["expect"])
        except AssertionError as exc:
            raise AssertionError(f"{blueprint_id} case {i}: {exc}") from exc
        assert run["cost_usd"] >= 0 and run["steps"]


def test_interrupt_survives_runtime_restart(client, headers):
    r = client.post("/v1/runs", headers=headers, json={"blueprint_id": "sage-lens", "input": {"question": "hello"}, "wait": True}).json()
    assert r["status"] == "waiting_review" and r["review"]["options"]
    runtime.reset_runtime()  # simulate an API restart: graphs and checkpointer connection are rebuilt from disk
    resumed = client.post(f"/v1/runs/{r['id']}/resume?wait=true", headers=headers, json={"answer": "Tesla"})
    assert resumed.status_code == 200
    final = client.get(f"/v1/runs/{r['id']}", headers=headers).json()
    assert final["status"] == "completed" and final["output"]["company"] == "Tesla"


def test_runs_are_metered_and_listed(client, headers):
    before = client.get("/v1/usage/breakdown?days=1&by=feature", headers=headers).json()
    run = _run(client, headers, "knowledge-qa", {"question": "hotel limit"})
    assert run["cost_usd"] > 0 and run["tokens_in"] > 0
    after = client.get("/v1/usage/breakdown?days=1&by=feature", headers=headers).json()
    agent_before = next((r["requests"] for r in before["rows"] if r["key"] == "agent"), 0)
    agent_after = next((r["requests"] for r in after["rows"] if r["key"] == "agent"), 0)
    assert agent_after > agent_before
    listing = client.get("/v1/runs?blueprint_id=knowledge-qa", headers=headers).json()
    assert any(r["id"] == run["id"] for r in listing["runs"])
    other = {**headers, "X-User-Id": "u9", "X-User-Email": "ravi@playground.local", "X-User-Role": "explorer"}
    assert client.get(f"/v1/runs/{run['id']}", headers=other).status_code == 404
    datasets = client.get("/v1/data", headers=headers).json()["datasets"]
    assert {d["id"] for d in datasets} >= {"invoices", "sales", "policies"}
