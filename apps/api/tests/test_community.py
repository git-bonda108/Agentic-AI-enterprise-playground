"""Batch 8: showcase, challenges judged by rubric, achievements, leaderboards, adoption analytics and the platform agents."""

from __future__ import annotations


def _run(client, headers, blueprint_id, payload):
    r = client.post("/v1/runs", headers=headers, json={"blueprint_id": blueprint_id, "input": payload, "wait": True})
    assert r.status_code == 201, r.text
    return r.json()


def test_showcase_publish_draft_like_comment(client, headers):
    run = _run(client, headers, "knowledge-qa", {"question": "What is the hotel limit per night?"})
    draft = client.post("/v1/community/showcase/draft", headers=headers, json={"run_id": run["id"]}).json()
    assert draft["draft"]["title"] and draft["draft"]["tags"] and draft["draft"]["source"] == f"run:{run['id']}"
    body = {"kind": "run", "ref_id": run["id"], "title": draft["draft"]["title"], "summary": draft["draft"]["summary"], "outcome": "Answered from policy in 2 seconds", "tags": ["policies", "Finance "]}
    item = client.post("/v1/community/showcase", headers=headers, json=body).json()
    assert item["owner_name"] == "Satya Bonda" and item["tags"] == ["policies", "finance"] and item["link"].endswith(run["id"])
    other = {**headers, "X-User-Id": "u9", "X-User-Email": "ravi@playground.local", "X-User-Role": "builder", "X-User-Name": "Ravi"}
    assert client.post("/v1/community/showcase", headers=other, json=body).status_code == 404  # not their run
    liked = client.post(f"/v1/community/showcase/{item['id']}/like", headers=other).json()
    assert liked == {"liked": True, "likes": 1}
    assert client.post(f"/v1/community/showcase/{item['id']}/like", headers=other).json()["likes"] == 0
    client.post(f"/v1/community/showcase/{item['id']}/like", headers=other)
    commented = client.post(f"/v1/community/showcase/{item['id']}/comments", headers=other, json={"body": "Nice one"}).json()
    assert commented["comments"][0]["user_name"] == "Ravi"
    listing = client.get("/v1/community/showcase?tag=finance&sort=top", headers=other).json()
    assert listing["items"][0]["id"] == item["id"] and listing["items"][0]["liked"] is True and listing["tags"]["finance"] == 1
    detail = client.get(f"/v1/community/showcase/{item['id']}", headers=headers).json()
    assert detail["views"] == 1 and len(detail["comments"]) == 1
    me = client.get("/v1/community/me", headers=headers).json()
    assert next(a for a in me["achievements"] if a["key"] == "publisher")["unlocked"] is True
    assert client.delete(f"/v1/community/showcase/{item['id']}", headers=other).status_code == 404
    assert client.delete(f"/v1/community/showcase/{item['id']}", headers=headers).status_code == 204


def test_challenge_lifecycle_judged_by_rubric(client, headers):
    builder = {**headers, "X-User-Id": "u9", "X-User-Email": "ravi@playground.local", "X-User-Role": "builder", "X-User-Name": "Ravi", "X-User-Department": "Finance"}
    assert client.post("/v1/community/challenges", headers=builder, json={"title": "Not allowed", "brief": "Builders cannot open challenges.", "cases": [{"input": {"question": "q"}}]}).status_code == 403
    ch = client.post("/v1/community/challenges", headers=headers, json={
        "title": "Policy answers sprint", "brief": "Build an agent that answers policy questions with a citation.",
        "cases": [{"input": {"question": "What is the hotel limit per night?"}, "expect": {"status": "completed", "contains": "POL-001"}}, {"input": {"question": "What do I need for a purchase over 50,000 USD?"}, "expect": {"contains": "POL-002"}}],
        "rubric": {"criteria": [{"id": "correctness", "weight": 1}, {"id": "groundedness", "weight": 1}], "pass_threshold": 3.0}, "badge": "Policy pro", "days_open": 3,
    }).json()
    assert ch["status"] == "open" and ch["time_left_h"] > 70 and ch["submission_count"] == 0
    agent = client.post("/v1/custom-agents", headers=builder, json={"name": "Ravi policy bot", "description": "Answers policy questions with citations.", "instructions": "Answer policy questions from the policies provided and cite the policy id in brackets.", "knowledge": ["policies"], "published": True}).json()
    assert client.post(f"/v1/community/challenges/{ch['id']}/submit", headers=builder, json={"agent_id": "nope"}).status_code == 404
    sub = client.post(f"/v1/community/challenges/{ch['id']}/submit", headers=builder, json={"agent_id": agent["id"], "note": "Cites every answer"}).json()
    client.post(f"/v1/community/challenges/{ch['id']}/submit", headers=headers, json={"agent_id": "knowledge-qa", "note": "The built-in one"})
    assert sub["submission_count"] == 1
    assert client.post(f"/v1/community/challenges/{ch['id']}/judge", headers=builder).status_code == 403
    judged = client.post(f"/v1/community/challenges/{ch['id']}/judge", headers=headers).json()
    assert judged["judged_now"] == 2 and all(s["score"] is not None and s["rank"] for s in judged["submissions"])
    assert all(s["judged"]["cases"] == 2 for s in judged["submissions"])
    closed = client.post(f"/v1/community/challenges/{ch['id']}/close", headers=headers).json()
    assert closed["status"] == "closed" and closed["winner_submission_id"] in {s["id"] for s in closed["submissions"]}
    winner = next(s for s in closed["submissions"] if s["id"] == closed["winner_submission_id"])
    winner_headers = builder if winner["user_id"] == "u9" else headers
    me = client.get("/v1/community/me", headers=winner_headers).json()
    assert next(a for a in me["achievements"] if a["key"] == "champion")["unlocked"] is True
    assert client.post(f"/v1/community/challenges/{ch['id']}/submit", headers=builder, json={"agent_id": agent["id"]}).status_code == 409
    listing = client.get("/v1/community/challenges", headers=headers).json()["challenges"]
    assert any(c["id"] == ch["id"] for c in listing)
    client.delete(f"/v1/custom-agents/{agent['id']}", headers=builder)


def test_achievements_and_leaderboard(client, headers):
    me = client.get("/v1/community/me", headers=headers).json()
    assert me["total"] == 12 and me["unlocked"] >= 3
    keys = {a["key"]: a for a in me["achievements"]}
    assert keys["agent_runner"]["target"] == 10 and keys["agent_runner"]["progress"] >= 1
    board = client.get("/v1/community/leaderboard?by=user&days=30", headers=headers).json()
    assert board["rows"][0]["rank"] == 1 and board["points"]["challenge_wins"] == 100
    mine = next(r for r in board["rows"] if r["user_id"] == "u1")
    assert mine["requests"] > 0 and mine["outcomes"] > 0 and mine["points"] > 0
    depts = client.get("/v1/community/leaderboard?by=department", headers=headers).json()["rows"]
    assert depts[0]["people"] >= 1 and "AI Platform" in {d["department"] for d in depts}


def test_adoption_summary_matrix_and_assumptions(client, headers):
    s = client.get("/v1/adoption/summary?days=30", headers=headers).json()
    assert s["kpis"]["active_users"] >= 1 and s["kpis"]["outcomes"] > 0 and s["kpis"]["hours"] > 0
    agent_row = next(f for f in s["features"] if f["feature"] == "agent")
    assert agent_row["outcomes"] > 0 and agent_row["hours_saved"] == round(agent_row["outcomes"] * 25 / 60, 2)
    assert s["departments"][0]["hours_saved"] > 0 and s["kpis"]["roi"] is not None and s["weekly"]
    assert any(a["key"] == "hourly_value_usd" for a in s["assumptions"]) and "Estimates" in s["method"]
    builder = {**headers, "X-User-Id": "u9", "X-User-Email": "ravi@playground.local", "X-User-Role": "builder", "X-User-Department": "Finance"}
    assert client.put("/v1/adoption/assumptions", headers=builder, json={"values": {"hourly_value_usd": 10}}).status_code == 403
    updated = client.put("/v1/adoption/assumptions", headers=headers, json={"values": {"minutes_saved.agent": 50}}).json()
    assert next(a for a in updated["assumptions"] if a["key"] == "minutes_saved.agent")["value"] == 50
    s2 = client.get("/v1/adoption/summary?days=30", headers=headers).json()
    assert next(f for f in s2["features"] if f["feature"] == "agent")["hours_saved"] == round(agent_row["outcomes"] * 50 / 60, 2)
    scoped = client.get("/v1/adoption/summary?days=30", headers=builder).json()
    assert scoped["department"] == "Finance"


def test_adoption_digest_platform_agent(client, headers):
    r = client.post("/v1/adoption/digest", headers=headers, json={"days": 7, "audience": "executives"}).json()
    assert r["status"] == "completed" and r["blueprint_id"] == "adoption-digest"
    out = r["output"]
    assert out["digest_md"] and len(out["recommendations"]) == 3 and out["kpis"]["active_users"] >= 1 and out["top_features"]
    hub = client.get("/v1/blueprints", headers=headers).json()["blueprints"]
    assert {"adoption-digest", "showcase-writer"} <= {b["id"] for b in hub}
    assert sum(1 for e in client.get("/v1/catalog?family=Domain", headers=headers).json()["entries"]) == 6  # platform agents stay out of the catalog
