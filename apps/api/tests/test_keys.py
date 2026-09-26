"""Batch 10: personal provider keys, platform key scope, per-caller availability."""

import pathlib

from app import keys as keysmod
from app.catalog import BY_ID, CATALOG
from app.config import settings
from app.db import SessionLocal
from app.models import ProviderKey, User
from app.router import TIER_CANDIDATES
from app.security import assert_safe_configuration

EXPLORER = {
    "X-Internal-Key": "test-key",
    "X-User-Id": "u-keys-explorer",
    "X-User-Email": "keys.explorer@playground.local",
    "X-User-Name": "Keys Explorer",
    "X-User-Role": "explorer",
    "X-User-Department": "Finance",
}


def test_catalog_has_the_new_providers_and_valid_tier_candidates():
    providers = {m.provider for m in CATALOG}
    assert {"NVIDIA NIM", "Mistral", "xAI", "Groq", "Cohere"} <= providers
    assert len(CATALOG) >= 30
    nim = [m for m in CATALOG if m.provider == "NVIDIA NIM"]
    assert any("Nemotron" in m.name for m in nim) and any("Hermes" in m.name for m in nim)
    assert all(m.litellm_model.startswith("nvidia_nim/") for m in nim)
    for tier, ids in TIER_CANDIDATES.items():
        for model_id in ids:
            assert model_id in BY_ID, (tier, model_id)
            assert BY_ID[model_id].tier in ("Frontier", "Premium", "Workhorse", "Economy")
    assert set(keysmod.PROVIDERS) == providers


def test_keys_list_shows_every_provider_with_links(client, headers):
    body = client.get("/v1/keys", headers=headers).json()
    assert body["scope"] == "all"
    rows = {p["provider"]: p for p in body["providers"]}
    assert len(rows) == len(keysmod.PROVIDERS)
    assert rows["NVIDIA NIM"]["key_page"].startswith("https://build.nvidia.com")
    assert rows["OpenAI"]["docs"].startswith("https://")
    assert all(p["personal"] is None for p in rows.values())
    assert all(p["models"] >= 1 for p in rows.values())


def test_personal_key_roundtrip_is_encrypted_and_only_last4_is_returned(client, headers):
    bad = client.put("/v1/keys/NVIDIA NIM", json={"key": "sk-not-an-nvidia-key"}, headers=headers)
    assert bad.status_code == 400 and "nvapi-" in bad.json()["detail"]
    assert client.put("/v1/keys/Nope", json={"key": "nvapi-abcdefgh1234"}, headers=headers).status_code == 404
    azure = client.put("/v1/keys/Azure OpenAI", json={"key": "0123456789abcdef"}, headers=headers)
    assert azure.status_code == 400 and "endpoint" in azure.json()["detail"]

    res = client.put("/v1/keys/NVIDIA NIM", json={"key": "nvapi-secret-value-ABCD"}, headers=headers)
    assert res.status_code == 200 and res.json() == {"provider": "NVIDIA NIM", "last4": "ABCD", "source": "personal"}
    body = client.get("/v1/keys", headers=headers).json()
    row = next(p for p in body["providers"] if p["provider"] == "NVIDIA NIM")
    assert row["personal"]["last4"] == "ABCD" and row["source"] == "personal"
    assert "nvapi-secret-value" not in res.text and "nvapi-secret-value" not in client.get("/v1/keys", headers=headers).text

    with SessionLocal() as db:
        stored = db.query(ProviderKey).filter_by(user_id="u1", provider="NVIDIA NIM").one()
        assert "nvapi-secret-value" not in stored.ciphertext
        assert keysmod.decrypt(stored.ciphertext) == "nvapi-secret-value-ABCD"
    assert keysmod.decrypt("not-a-token") is None

    # replacing the key keeps one row; removing it returns 204 then 404
    client.put("/v1/keys/NVIDIA NIM", json={"key": "nvapi-second-value-WXYZ"}, headers=headers)
    with SessionLocal() as db:
        assert db.query(ProviderKey).filter_by(user_id="u1", provider="NVIDIA NIM").count() == 1
    assert client.delete("/v1/keys/NVIDIA NIM", headers=headers).status_code == 204
    assert client.delete("/v1/keys/NVIDIA NIM", headers=headers).status_code == 404


def test_availability_follows_personal_keys_and_admin_scope(client, headers, monkeypatch):
    """With the fake provider off, models light up per caller: your key, or the platform key when the scope allows it."""
    monkeypatch.setattr(settings, "fake_llm", False)
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-platform-key-for-tests")
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    client.get("/v1/models", headers=EXPLORER)  # creates the explorer

    # nobody has a Mistral key
    models = {m["id"]: m for m in client.get("/v1/models", headers=EXPLORER).json()["models"]}
    assert models["mistral-small-4"]["available"] is False and models["mistral-small-4"]["key_source"] == "none"
    assert models["gpt-5-nano"]["available"] is True and models["gpt-5-nano"]["key_source"] == "platform"

    # the explorer adds their own Mistral key: only they see Mistral light up
    assert client.put("/v1/keys/Mistral", json={"key": "mistral-personal-key-1234"}, headers=EXPLORER).status_code == 200
    models = {m["id"]: m for m in client.get("/v1/models", headers=EXPLORER).json()["models"]}
    assert models["mistral-small-4"]["available"] is True and models["mistral-small-4"]["key_source"] == "personal"
    admin_models = {m["id"]: m for m in client.get("/v1/models", headers=headers).json()["models"]}
    assert admin_models["mistral-small-4"]["available"] is False

    # a chat on a provider without any key is blocked with a helpful message, and lands in the ledger as blocked
    with client.stream("POST", "/v1/chat/stream", json={"model": "grok-4-3", "messages": [{"role": "user", "content": "hi"}], "persist": False}, headers=EXPLORER) as res:
        text = "".join(res.iter_text())
    assert "event: error" in text and "Add your own xAI key" in text

    # the admin restricts platform keys to the product's own agents
    assert client.put("/v1/keys/admin/scope", json={"scope": "platform-only"}, headers=EXPLORER).status_code == 403
    try:
        assert client.put("/v1/keys/admin/scope", json={"scope": "platform-only"}, headers=headers).json() == {"scope": "platform-only"}
        models = {m["id"]: m for m in client.get("/v1/models", headers=EXPLORER).json()["models"]}
        assert models["gpt-5-nano"]["available"] is False, "platform key no longer serves people"
        assert models["mistral-small-4"]["available"] is True, "personal keys still work"
        with SessionLocal() as db:
            for_judge = keysmod.available_providers(db, None, "eval")
            assert for_judge.get("OpenAI") == "platform" and set(for_judge.values()) == {"platform"}, "the judge and canaries keep the platform keys"
            explorer = db.get(User, "u-keys-explorer")
            secret, source, _ = keysmod.resolve_key(db, explorer.id, "Mistral", "chat")
            assert (secret, source) == ("mistral-personal-key-1234", "personal")
            assert keysmod.resolve_key(db, explorer.id, "OpenAI", "chat")[1] == "none"
            assert keysmod.resolve_key(db, explorer.id, "OpenAI", "canary")[1] == "platform"
    finally:
        assert client.put("/v1/keys/admin/scope", json={"scope": "all"}, headers=headers).json() == {"scope": "all"}
        client.delete("/v1/keys/Mistral", headers=EXPLORER)


def test_key_test_endpoint_uses_the_cheapest_model(client, headers):
    body = client.post("/v1/keys/Groq/test", headers=headers).json()
    assert body["ok"] is True and body["model"] == "groq-gpt-oss-20b" and body["source"] == "fake"
    assert client.post("/v1/keys/Nope/test", headers=headers).status_code == 404


def test_usage_summary_and_breakdown_split_by_key_source(client, headers):
    with client.stream("POST", "/v1/chat/stream", json={"model": "gpt-5-nano", "messages": [{"role": "user", "content": "key source please"}], "persist": False}, headers=headers) as res:
        text = "".join(res.iter_text())
    assert '"key_source": "fake"' in text
    summary = client.get("/v1/usage/summary?days=1", headers=headers).json()
    assert any(r["key_source"] == "fake" for r in summary["by_key_source"])
    breakdown = client.get("/v1/usage/breakdown?days=1&by=key_source", headers=headers).json()
    assert breakdown["rows"] or breakdown.get("items") or breakdown


def test_admin_settings_reports_scope_and_encryption(client, headers):
    body = client.get("/v1/admin/settings", headers=headers).json()
    assert body["key_scope"] == "all" and body["key_encryption"] in ("configured", "derived-from-internal-key")
    nim = next(p for p in body["providers"] if p["provider"] == "NVIDIA NIM")
    assert nim["env_key"] == "NVIDIA_NIM_API_KEY" and nim["key_page"]


def test_production_guard_wants_an_explicit_encryption_key(monkeypatch):
    monkeypatch.setattr(settings, "key_encryption_key", "")
    assert any("PLAYGROUND_KEY_ENCRYPTION_KEY" in p for p in assert_safe_configuration())
    monkeypatch.setattr(settings, "key_encryption_key", "x" * 44)
    assert not any("PLAYGROUND_KEY_ENCRYPTION_KEY" in p for p in assert_safe_configuration())
    example = pathlib.Path(__file__).resolve().parents[3] / ".env.example"
    assert "PLAYGROUND_KEY_ENCRYPTION_KEY" in example.read_text()
