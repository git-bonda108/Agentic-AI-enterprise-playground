def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["fake_llm"] is True


def test_models_require_internal_key(client):
    assert client.get("/v1/models").status_code == 401


def test_models_list(client, headers):
    body = client.get("/v1/models", headers=headers).json()
    assert len(body["models"]) >= 10
    assert {"id", "provider", "input_per_m", "available"} <= set(body["models"][0].keys())
