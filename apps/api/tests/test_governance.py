import json


def sse(text: str):
    out = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        ev, data = None, None
        for line in block.splitlines():
            if line.startswith("event:"):
                ev = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
        if ev:
            out.append((ev, data))
    return out


def explorer(headers):
    return {**headers, "X-User-Id": "u5", "X-User-Email": "carlos@playground.local", "X-User-Name": "Carlos Mendes", "X-User-Role": "explorer", "X-User-Department": "Sales"}


def test_explorer_cannot_use_frontier_model(client, headers):
    with client.stream("POST", "/v1/chat/stream", headers=explorer(headers), json={"model": "claude-fable-5-1", "messages": [{"role": "user", "content": "hi"}], "persist": False}) as r:
        events = sse("".join(r.iter_text()))
    err = next(d for e, d in events if e == "error")
    assert err["code"] == "blocked" and "explorer" in err["message"]
    body = client.get("/v1/usage/breakdown?days=1&by=model", headers=explorer(headers)).json()
    assert body["totals"]["errors"] >= 1


def test_models_endpoint_marks_allowed_per_role(client, headers):
    admin = client.get("/v1/models", headers=headers).json()
    assert all(m["allowed"] for m in admin["models"] if m["tier"] == "Frontier")
    exp = client.get("/v1/models", headers=explorer(headers)).json()
    assert not any(m["allowed"] for m in exp["models"] if m["tier"] == "Frontier")
    assert any(m["allowed"] for m in exp["models"] if m["tier"] == "Economy")


def test_admin_endpoints_require_admin_role(client, headers):
    assert client.get("/v1/admin/users", headers=explorer(headers)).status_code == 403
    assert client.get("/v1/admin/users", headers=headers).status_code == 200


def test_budget_cap_blocks_and_raises_alert(client, headers):
    carlos = explorer(headers)
    # Spend a little so the ledger has a row for Carlos, then cap him below it.
    with client.stream("POST", "/v1/chat/stream", headers=carlos, json={"model": "claude-haiku-4-5", "messages": [{"role": "user", "content": "one small call"}], "persist": False}) as r:
        events = sse("".join(r.iter_text()))
    assert any(e == "usage" for e, _ in events)
    budgets = client.get("/v1/admin/budgets", headers=headers).json()
    put = client.put("/v1/admin/budgets", headers=headers, json={
        "org_cap_usd": budgets["org_cap_usd"], "default_user_cap_usd": budgets["default_user_cap_usd"],
        "user_caps": {"u5": 0.000001}, "department_caps": {},
    })
    assert put.status_code == 200
    with client.stream("POST", "/v1/chat/stream", headers=carlos, json={"model": "claude-haiku-4-5", "messages": [{"role": "user", "content": "again"}], "persist": False}) as r:
        events = sse("".join(r.iter_text()))
    err = next(d for e, d in events if e == "error")
    assert "monthly cap" in err["message"]
    alerts = client.get("/v1/alerts", headers=headers).json()["alerts"]
    assert any(a["scope"] == "user" and a["key"] == "u5" and a["threshold"] == 100 for a in alerts)
    mine = client.get("/v1/alerts", headers=carlos).json()["alerts"]
    assert mine and all(a["key"] == "u5" for a in mine)
    ack = client.post(f"/v1/alerts/{mine[0]['id']}/ack", headers=carlos)
    assert ack.status_code == 200
    # restore
    client.put("/v1/admin/budgets", headers=headers, json={"org_cap_usd": budgets["org_cap_usd"], "default_user_cap_usd": budgets["default_user_cap_usd"], "user_caps": {}, "department_caps": {}})


def test_policy_roundtrip_and_reset(client, headers):
    body = {"allowed_tiers": ["Economy"], "allowed_providers": ["Anthropic"], "max_tokens": 1024, "smart_enabled": False}
    put = client.put("/v1/admin/policies/explorer", headers=headers, json=body).json()
    assert put["allowed_tiers"] == ["Economy"] and put["smart_enabled"] is False
    preview = client.post("/v1/route/preview", headers=explorer(headers), json={"prompt": "hello"}).json()
    assert preview["enabled"] is False
    assert client.post("/v1/admin/policies/reset", headers=headers).status_code == 200
    pol = client.get("/v1/admin/policies", headers=headers).json()
    assert next(p for p in pol["policies"] if p["role"] == "explorer")["allowed_tiers"] == ["Economy", "Workhorse"]


def test_breakdown_reconciles_with_summary(client, headers):
    summary = client.get("/v1/usage/summary?days=7", headers=headers).json()
    for layer in ("model", "user", "feature", "provider", "department", "day", "conversation"):
        body = client.get(f"/v1/usage/breakdown?days=7&by={layer}", headers=headers).json()
        assert abs(sum(r["cost_usd"] for r in body["rows"]) - summary["spend_window_usd"]) < 1e-6, layer
        assert body["totals"]["requests"] == summary["requests"]


def test_admin_user_role_change(client, headers):
    users = client.get("/v1/admin/users", headers=headers).json()["users"]
    assert any(u["id"] == "u5" for u in users)
    patched = client.patch("/v1/admin/users/u5", headers=headers, json={"role": "builder"}).json()
    assert patched["role"] == "builder"
    client.patch("/v1/admin/users/u5", headers=headers, json={"role": "explorer"})
    settings = client.get("/v1/admin/settings", headers=headers).json()
    assert settings["fake_llm"] is True and settings["providers"]
