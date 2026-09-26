"""An OpenAI-compatible gateway, so any SDK that speaks the Chat Completions API runs through the playground.

Point a client at `<api>/openai/v1` with a personal token as the API key: the same policies, budgets, Smart routing,
key resolution and ledger apply as in the playground pages. `model` may be any catalog id or `smart`. Calls are
metered as feature `sdk`; an `X-Trace-Id` header (or `metadata.trace_id`) groups them into one trace.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.catalog import CATALOG, estimate_cost, get_model
from app.db import get_db
from app.governance import allowed_model_ids, check_budget, check_policy, policy_for
from app.keys import available_providers, resolve_key
from app.llm import ProviderError, complete, complete_with_tools, stream_completion
from app.models import UsageEvent, User
from app.router import SMART, route
from app.routers.mcp import mcp_user

logger = logging.getLogger("playground.gateway")
router = APIRouter(prefix="/openai/v1", tags=["openai-compatible"])
FEATURE = "sdk"
DEFAULT_MAX_TOKENS = 4096


class ChatCompletionRequest(BaseModel):
    model: str = SMART
    messages: list[dict[str, Any]] = Field(min_length=1)
    temperature: float | None = None
    max_tokens: int | None = Field(default=None, ge=1)
    max_completion_tokens: int | None = Field(default=None, ge=1)
    top_p: float | None = None
    stream: bool = False
    stream_options: dict[str, Any] | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: Any | None = None
    metadata: dict[str, Any] | None = None
    user: str | None = None


def _error(status: int, message: str, code: str) -> JSONResponse:
    return JSONResponse({"error": {"message": message, "type": "invalid_request_error" if status < 500 else "server_error", "code": code}}, status_code=status)


def _clean_messages(messages: list[dict]) -> list[dict]:
    """Providers accept the OpenAI shapes as they are; only null content needs normalising for the fake provider."""
    out = []
    for m in messages:
        mm = dict(m)
        if mm.get("content") is None:
            mm["content"] = ""
        if isinstance(mm.get("content"), list):  # content parts: keep the text
            mm["content"] = "\n".join(p.get("text", "") for p in mm["content"] if isinstance(p, dict) and p.get("type") == "text")
        out.append(mm)
    return out


@router.get("/models")
def list_models(user: User = Depends(mcp_user), db: Session = Depends(get_db)) -> dict:
    providers = available_providers(db, user, FEATURE)
    allowed = allowed_model_ids(db, user.role)
    data = [{"id": SMART, "object": "model", "created": 0, "owned_by": "playground"}]
    data += [{"id": m.id, "object": "model", "created": 0, "owned_by": m.provider} for m in CATALOG if m.provider in providers and m.id in allowed]
    return {"object": "list", "data": data}


@router.post("/chat/completions")
async def chat_completions(req: ChatCompletionRequest, user: User = Depends(mcp_user), db: Session = Depends(get_db), x_trace_id: str = Header(default="")):
    trace_id = (x_trace_id or (req.metadata or {}).get("trace_id") or "")[:64] or None
    routed, routed_tier, baseline = False, None, None
    model_id = req.model
    if model_id == SMART:
        if not policy_for(db, user.role).smart_enabled:
            return _error(403, "Smart routing is disabled for your role.", "smart_disabled")
        prompt = next((str(m.get("content", "")) for m in reversed(req.messages) if m.get("role") == "user"), "")
        decision = route(prompt, allowed_model_ids(db, user.role), providers=set(available_providers(db, user, FEATURE)))
        if decision is None:
            return _error(402, "No model with a usable key is available for your role. Add a provider key in the playground.", "no_model")
        model_id, routed, routed_tier, baseline = decision.model, True, decision.tier, decision.baseline_model
    spec = get_model(model_id)
    if spec is None:
        return _error(404, f"The model '{model_id}' does not exist in the playground catalog.", "model_not_found")
    denial = check_policy(db, user, spec)
    if denial:
        return _error(403, denial, "policy")
    budget = check_budget(db, user)
    if not budget.allowed:
        return _error(402, budget.reason or "Budget exceeded", "budget")
    api_key, key_source, extra = resolve_key(db, user.id, spec.provider, FEATURE)
    if key_source == "none":
        return _error(402, f"No {spec.provider} key is available. Add your own key in the playground or ask an admin to enable the platform key.", "no_key")
    policy = policy_for(db, user.role)
    # A client that sets no limit gets a sane default rather than the policy ceiling: providers reject limits above a model's maximum output.
    max_tokens = min(req.max_tokens or req.max_completion_tokens or DEFAULT_MAX_TOKENS, policy.max_tokens)
    messages = _clean_messages(req.messages)
    created = int(time.time())
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    common = {"id": completion_id, "object": "chat.completion", "created": created, "model": model_id, "system_fingerprint": "enterprise-ai-playground"}

    def meter(usage, status: str = "ok", latency_ms: int | None = None) -> None:
        savings = max(estimate_cost(baseline, usage.tokens_in, usage.tokens_out, usage.tokens_cached) - usage.cost_usd, 0.0) if (routed and baseline and usage) else 0.0
        db.add(UsageEvent(
            user_id=user.id, feature=FEATURE, model=model_id, provider=spec.provider, status=status,
            tokens_in=usage.tokens_in if usage else 0, tokens_out=usage.tokens_out if usage else 0, tokens_cached=usage.tokens_cached if usage else 0,
            cost_usd=usage.cost_usd if usage else 0.0, latency_ms=usage.latency_ms if usage else (latency_ms or 0),
            routed=routed, routed_tier=routed_tier, savings_usd=round(savings, 8), key_source=key_source, trace_id=trace_id,
        ))
        db.commit()

    if req.stream:
        async def events():
            started = time.perf_counter()
            yield {"data": json.dumps({**common, "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}]})}
            try:
                async for item in stream_completion(model_id, messages, {"temperature": req.temperature, "max_tokens": max_tokens, "top_p": req.top_p}, api_key=api_key, api_base=extra.get("api_base")):
                    if item["type"] == "delta":
                        yield {"data": json.dumps({**common, "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {"content": item["text"]}, "finish_reason": None}]})}
                    elif item["type"] == "usage":
                        u = item["usage"]
                        meter(u)
                        final = {**common, "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
                        if (req.stream_options or {}).get("include_usage"):
                            final["usage"] = {"prompt_tokens": u.tokens_in, "completion_tokens": u.tokens_out, "total_tokens": u.tokens_in + u.tokens_out, "playground": {"cost_usd": u.cost_usd, "key_source": key_source, "routed": routed}}
                        yield {"data": json.dumps(final)}
            except ProviderError as exc:
                meter(None, "error", int((time.perf_counter() - started) * 1000))
                yield {"data": json.dumps({"error": {"message": str(exc), "type": "server_error", "code": "provider_error"}})}
            yield {"data": "[DONE]"}

        return EventSourceResponse(events(), ping=15)

    started = time.perf_counter()
    try:
        if req.tools:
            text, calls, usage = complete_with_tools(model_id, messages, req.tools, max_tokens=max_tokens, temperature=req.temperature if req.temperature is not None else 0.2, api_key=api_key, api_base=extra.get("api_base"))
        else:
            text, usage = complete(model_id, messages, max_tokens=max_tokens, temperature=req.temperature if req.temperature is not None else 0.2, api_key=api_key, api_base=extra.get("api_base"))
            calls = []
    except ProviderError as exc:
        meter(None, "error", int((time.perf_counter() - started) * 1000))
        return _error(502, str(exc), "provider_error")
    meter(usage)
    message: dict[str, Any] = {"role": "assistant", "content": text or None}
    if calls:
        message["tool_calls"] = [{"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": json.dumps(c.get("arguments") or {})}} for c in calls]
    return {
        **common,
        "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if calls else "stop", "logprobs": None}],
        "usage": {"prompt_tokens": usage.tokens_in, "completion_tokens": usage.tokens_out, "total_tokens": usage.tokens_in + usage.tokens_out, "playground": {"cost_usd": usage.cost_usd, "latency_ms": usage.latency_ms, "key_source": key_source, "routed": routed, "routed_tier": routed_tier}},
    }
