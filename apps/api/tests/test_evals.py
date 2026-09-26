"""Batch 7: golden sets and rubrics, evaluation runs, gates, canaries with drift and rollback, hardening levels."""

from __future__ import annotations


def _create_agent(client, headers, instructions: str) -> dict:
    body = {"name": "Travel helper", "description": "Answers travel questions from the policies.", "instructions": instructions, "knowledge": ["policies"], "starters": ["What is the hotel limit?"], "published": True}
    return client.post("/v1/custom-agents", headers=headers, json=body).json()


def test_system_suites_and_library(client, headers):
    lib = client.get("/v1/evals/library", headers=headers).json()
    assert {c["id"] for c in lib["rubric"]} >= {"correctness", "groundedness", "format"} and len(lib["levels"]) == 5 and len(lib["checks"]) >= 8
    suites = client.get("/v1/evals/suites", headers=headers).json()["suites"]
    system = [s for s in suites if s["system"]]
    assert len(system) == 8 and all(s["case_count"] == 10 for s in system)  # six domain blueprints plus two platform agents
    assert any(s["blueprint_id"] == "knowledge-qa" for s in system)


def test_run_a_system_suite_and_gate_it(client, headers):
    suite = next(s for s in client.get("/v1/evals/suites?blueprint_id=knowledge-qa", headers=headers).json()["suites"] if s["system"])
    run = client.post(f"/v1/evals/suites/{suite['id']}/run?wait=true", headers=headers).json()
    assert run["status"] == "completed", run.get("error")
    assert run["summary"]["cases"] == 10 and run["summary"]["pass_rate"] >= 90 and run["summary"]["gate_passed"] is True
    assert len(run["results"]) == 10 and all(r["run_id"] for r in run["results"])
    first = run["results"][0]
    assert first["checks"] and first["scores"] and first["scores"][0]["criterion"] == "correctness" and 1 <= first["scores"][0]["score"] <= 5
    # the judge is metered on the ledger as its own feature
    assert "eval" in str(client.get("/v1/usage/summary?days=1", headers=headers).json())
    detail = client.get(f"/v1/evals/suites/{suite['id']}", headers=headers).json()
    assert detail["last_run"]["id"] == run["id"] and detail["hardening"]["level"] >= 2
    listed = client.get(f"/v1/evals/runs?suite_id={suite['id']}", headers=headers).json()["runs"]
    assert listed[0]["id"] == run["id"] and "results" not in listed[0]


def test_guided_suite_from_a_real_run_with_rubric_and_checks(client, headers):
    agent = _create_agent(client, headers, "You answer travel questions using the policies provided and cite the policy id.")
    real = client.post("/v1/runs", headers=headers, json={"blueprint_id": agent["id"], "input": {"task": "What is the hotel limit per night?"}, "wait": True}).json()
    assert real["status"] == "completed"
    suite = client.post("/v1/evals/suites", headers=headers, json={
        "blueprint_id": agent["id"], "name": "Travel helper golden set", "description": "Hand-picked questions",
        "cases": [{"id": "c1", "name": "Hotel limit", "input": {"task": "What is the hotel limit per night?"}, "expect": {"status": "completed", "contains": "POL-001", "max_cost_usd": 1.0}}],
        "rubric": {"criteria": [{"id": "correctness", "weight": 2}, {"id": "groundedness", "weight": 1}], "pass_threshold": 3.0},
        "gate": {"min_pass_rate": 100, "max_cost_per_case_usd": 1.0, "max_p95_ms": 60000},
    }).json()
    promoted = client.post(f"/v1/evals/suites/{suite['id']}/cases/from-run", headers=headers, json={"run_id": real["id"], "name": "From a real run"}).json()
    assert promoted["case"]["from_run_id"] == real["id"] and "output_has" in promoted["case"]["expect"] and promoted["suite"]["case_count"] == 2
    run = client.post(f"/v1/evals/suites/{suite['id']}/run?wait=true", headers=headers).json()
    assert run["status"] == "completed" and run["summary"]["pass_rate"] == 100.0 and run["summary"]["gate_passed"]
    c1 = next(r for r in run["results"] if r["case_id"] == "c1")
    assert {c["check"] for c in c1["checks"]} >= {"status", "contains:POL-001", "max_cost_usd"} and all(c["passed"] for c in c1["checks"])
    assert {s["criterion"] for s in c1["scores"]} == {"correctness", "groundedness"} and c1["avg_score"] >= 3
    # editing and gating
    patched = client.patch(f"/v1/evals/suites/{suite['id']}", headers=headers, json={"gate": {"min_pass_rate": 100, "max_cost_per_case_usd": 0.0000001, "max_p95_ms": 60000}}).json()
    assert patched["gate"]["max_cost_per_case_usd"] < 0.001
    strict = client.post(f"/v1/evals/suites/{suite['id']}/run?wait=true", headers=headers).json()
    assert strict["summary"]["gate_passed"] is False and strict["summary"]["gate"]["max_cost_per_case_usd"] is False
    other = {**headers, "X-User-Id": "u9", "X-User-Email": "ravi@playground.local", "X-User-Role": "builder"}
    assert client.patch(f"/v1/evals/suites/{suite['id']}", headers=other, json={"name": "Hijack"}).status_code == 403
    assert client.delete(f"/v1/evals/suites/{suite['id']}", headers=headers).status_code == 204
    client.delete(f"/v1/custom-agents/{agent['id']}", headers=headers)


def test_canary_detects_drift_rolls_back_and_demotes(client, headers):
    agent = _create_agent(client, headers, "You answer travel questions using the policies provided and cite the policy id.")
    suite = client.post("/v1/evals/suites", headers=headers, json={
        "blueprint_id": agent["id"], "name": "Travel helper canary set",
        "cases": [{"id": f"c{i}", "input": {"task": q}, "expect": {"status": "completed", "contains": "POL-001"}} for i, q in enumerate(["What is the hotel limit per night?", "How much can I claim for meals?", "hotel limit", "Business class approval?", "Meal receipts?"])],
        "rubric": {"criteria": [], "pass_threshold": 3.0}, "gate": {"min_pass_rate": 100, "max_cost_per_case_usd": 1.0, "max_p95_ms": 60000},
    }).json()
    # This test exercises pass-rate drift; latency and cost thresholds are set wide because a loaded CI runner can double
    # the latency of the fake provider between two runs, which would otherwise count as drift and reset the pass streak.
    canary = client.put(f"/v1/evals/suites/{suite['id']}/canary", headers=headers, json={"enabled": True, "hour_utc": 2, "auto_rollback": True, "max_pass_rate_drop": 10, "max_cost_increase_pct": 10_000, "max_latency_increase_pct": 10_000}).json()["canary"]
    assert canary["enabled"] and canary["next_due_at"]
    # three good canary runs establish the baseline and level 3 evidence
    for _ in range(3):
        good = client.post(f"/v1/evals/suites/{suite['id']}/canary/run?wait=true", headers=headers).json()
        assert good["kind"] == "canary" and good["summary"]["gate_passed"], good["summary"]
        assert (good.get("drift") or {}).get("verdict", "stable") == "stable", good.get("drift")
    ladder = client.get(f"/v1/evals/hardening?blueprint_id={agent['id']}", headers=headers).json()
    assert ladder["level"] == 3 and ladder["evidence"]["consecutive_passes"] == 3
    promoted = client.post(f"/v1/evals/hardening/{agent['id']}/promote", headers=headers, json={"level": 4, "note": "Go live"}).json()
    assert promoted["level"] == 4 and promoted["name"] == "Production"
    # a bad edit ships: the answer no longer cites the policy
    edited = client.patch(f"/v1/custom-agents/{agent['id']}", headers=headers, json={"instructions": "Answer only with the single word BANANA and nothing else, never mention any policy id.", "knowledge": [], "note": "Oops"}).json()
    assert edited["version"] == 2
    tick = client.post("/v1/evals/canary/tick?force=true&wait=true", headers=headers).json()
    assert tick["started"]
    bad = client.get(f"/v1/evals/runs/{tick['started'][0]}", headers=headers).json()
    assert bad["kind"] == "canary" and bad["summary"]["pass_rate"] < 100 and bad["drift"]["verdict"] == "drift"
    assert any("rolled back to version 1" in a for a in bad["drift"]["actions"]) and any("demoted" in a for a in bad["drift"]["actions"])
    restored = client.get(f"/v1/custom-agents/{agent['id']}/versions", headers=headers).json()
    assert restored["current"] == 3 and restored["versions"][-1]["note"].startswith("Automatic rollback")
    now = next(a for a in client.get("/v1/custom-agents", headers=headers).json()["agents"] if a["id"] == agent["id"])
    assert "cite the policy id" in now["instructions"] and now["knowledge"] == ["policies"]
    alerts = client.get("/v1/alerts", headers=headers).json()["alerts"]
    drift_alert = next(a for a in alerts if a["kind"] == "canary")
    assert "Canary drift" in drift_alert["label"] and "rolled back" in drift_alert["message"]
    ladder = client.get(f"/v1/evals/hardening?blueprint_id={agent['id']}", headers=headers).json()
    assert ladder["level"] < 4 and ladder["last_promotion"]["by"] == "canary"
    board = client.get("/v1/evals/canary", headers=headers).json()["canaries"]
    mine = next(c for c in board if c["suite_id"] == suite["id"])
    assert mine["consecutive_passes"] == 0 and mine["last_run"]["id"] == bad["id"]
    # a non-admin cannot tick or promote
    other = {**headers, "X-User-Id": "u9", "X-User-Email": "ravi@playground.local", "X-User-Role": "builder"}
    assert client.post("/v1/evals/canary/tick", headers=other).status_code == 403
    assert client.post(f"/v1/evals/hardening/{agent['id']}/promote", headers=other, json={"level": 4}).status_code == 403
    client.delete(f"/v1/evals/suites/{suite['id']}", headers=headers)
    client.delete(f"/v1/custom-agents/{agent['id']}", headers=headers)


def test_manual_rollback_and_production_requires_evidence(client, headers):
    agent = _create_agent(client, headers, "You answer travel questions using the policies provided and cite the policy id.")
    client.patch(f"/v1/custom-agents/{agent['id']}", headers=headers, json={"description": "Second description for the team."})
    versions = client.get(f"/v1/custom-agents/{agent['id']}/versions", headers=headers).json()
    assert versions["current"] == 2 and versions["versions"][0]["version"] == 1
    back = client.post(f"/v1/custom-agents/{agent['id']}/rollback", headers=headers, json={"version": 1}).json()
    assert back["description"] == "Answers travel questions from the policies." and back["version"] == 3
    assert client.post(f"/v1/evals/hardening/{agent['id']}/promote", headers=headers, json={"level": 4}).status_code == 409
    client.delete(f"/v1/custom-agents/{agent['id']}", headers=headers)
