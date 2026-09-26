"""Security middleware and start-up guards: response headers, a per-caller rate limit, and refusal to start unsafely in production."""

from __future__ import annotations

import threading
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings

DEFAULT_INTERNAL_KEY = "local-internal-key"
LOCAL_ENVIRONMENTS = {"local", "e2e", "test", "development"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Headers every API response carries. The API is never framed and never cached by intermediaries."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding one-minute window per caller (identity header, bearer token or client address). Health checks are exempt."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _caller(request: Request) -> str:
        return request.headers.get("x-user-id") or request.headers.get("authorization", "")[-24:] or (request.client.host if request.client else "anonymous")

    async def dispatch(self, request: Request, call_next) -> Response:
        limit = int(getattr(settings, "rate_limit_per_minute", 240) or 0)
        if limit <= 0 or request.url.path in ("/health", "/v1/meta"):
            return await call_next(request)
        now = time.monotonic()
        key = self._caller(request)
        with self._lock:
            window = [t for t in self._hits.get(key, []) if now - t < 60]
            if len(window) >= limit:
                self._hits[key] = window
                retry = int(60 - (now - window[0])) + 1
                return JSONResponse({"detail": f"Rate limit of {limit} requests per minute reached. Retry in {retry}s."}, status_code=429, headers={"Retry-After": str(retry)})
            window.append(now)
            self._hits[key] = window
            if len(self._hits) > 10_000:  # forget idle callers
                self._hits = {k: v for k, v in self._hits.items() if v and now - v[-1] < 60}
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - len(window)))
        return response


def assert_safe_configuration() -> list[str]:
    """Returns the list of problems. Outside local environments any problem stops the process from starting."""
    problems: list[str] = []
    if settings.internal_key == DEFAULT_INTERNAL_KEY:
        problems.append("PLAYGROUND_INTERNAL_KEY is the development default")
    if len(settings.internal_key) < 24:
        problems.append("PLAYGROUND_INTERNAL_KEY is shorter than 24 characters")
    if settings.fake_llm:
        problems.append("PLAYGROUND_FAKE_LLM is on")
    if settings.database_url.startswith("sqlite"):
        problems.append("PLAYGROUND_DATABASE_URL points at SQLite")
    if any(o.startswith("http://") for o in settings.cors_origins):
        problems.append("PLAYGROUND_CORS_ORIGINS allows a plain-http origin")
    if settings.environment in LOCAL_ENVIRONMENTS:
        return problems
    if problems:
        raise RuntimeError("Refusing to start in environment '" + settings.environment + "': " + "; ".join(problems))
    return problems
