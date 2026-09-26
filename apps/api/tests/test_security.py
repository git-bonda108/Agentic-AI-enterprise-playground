"""Batch 9: security headers, rate limiting, and the refusal to start with development settings outside local environments."""

from __future__ import annotations

import pytest

from app.config import settings
from app.security import assert_safe_configuration


def test_security_headers_on_every_response(client, headers):
    r = client.get("/v1/models", headers=headers)
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Cache-Control"] == "no-store"
    assert r.headers.get("X-Powered-By") is None


def test_rate_limit_returns_429_then_recovers(client, headers, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_per_minute", 5, raising=False)
    caller = {**headers, "X-User-Id": "burst-user", "X-User-Email": "burst@playground.local"}
    first = client.get("/v1/models", headers=caller)
    assert first.status_code == 200 and first.headers["X-RateLimit-Limit"] == "5" and first.headers["X-RateLimit-Remaining"] == "4"
    codes = [client.get("/v1/models", headers=caller).status_code for _ in range(6)]
    assert codes[:4] == [200] * 4 and codes[4] == 429
    r = client.get("/v1/models", headers=caller)
    assert r.status_code == 429 and "Retry-After" in r.headers and "per minute" in r.json()["detail"]
    assert client.get("/health").status_code == 200  # health is never limited
    monkeypatch.setattr(settings, "rate_limit_per_minute", 240, raising=False)
    assert client.get("/v1/models", headers=headers).status_code == 200


def test_production_guard_refuses_development_defaults(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(RuntimeError) as exc:
        assert_safe_configuration()
    message = str(exc.value)
    assert "PLAYGROUND_INTERNAL_KEY" in message and "SQLite" in message and "FAKE_LLM" in message
    monkeypatch.setattr(settings, "environment", "local")
    assert len(assert_safe_configuration()) >= 3  # reported, not fatal, locally
