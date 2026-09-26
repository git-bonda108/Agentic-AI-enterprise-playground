"""Streaming completions through LiteLLM, with a deterministic fake provider for tests."""

import asyncio
import json
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.catalog import estimate_cost, get_model
from app.config import settings


@dataclass
class Usage:
    tokens_in: int
    tokens_out: int
    tokens_cached: int
    cost_usd: float
    latency_ms: int


class ProviderError(Exception):
    pass


async def _fake_stream(model_id: str, messages: list[dict], params: dict) -> AsyncIterator[dict]:
    """Echo-style provider: predictable text, plausible token counts, zero network."""
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    spec = get_model(model_id)
    name = spec.name if spec else model_id
    text = f"Fake reply from {name}: you said \"{last_user[:120]}\". "
    text += "This is a deterministic response used for tests and offline demos."
    started = time.perf_counter()
    for word in text.split(" "):
        await asyncio.sleep(0.005)
        yield {"type": "delta", "text": word + " "}
    tokens_in = max(8, sum(len(m["content"]) for m in messages) // 4)
    tokens_out = max(4, len(text) // 4)
    yield {
        "type": "usage",
        "usage": Usage(tokens_in, tokens_out, 0, estimate_cost(model_id, tokens_in, tokens_out), int((time.perf_counter() - started) * 1000)),
    }


def _no_key_message(spec) -> str:
    return f"No {spec.provider} key is available for {spec.name}. Add your own {spec.provider} key from the Keys drawer, or ask an admin to enable the platform key ({spec.env_key})."


def _credentials(spec, api_key: str | None, api_base: str | None) -> dict:
    """LiteLLM credentials for one call: an explicit key wins; otherwise the platform key must be present in the environment."""
    if api_key:
        creds: dict = {"api_key": api_key}
        if api_base:
            creds["api_base"] = api_base
        return creds
    if not spec.available():
        raise ProviderError(_no_key_message(spec))
    return {}


async def _litellm_stream(model_id: str, messages: list[dict], params: dict, api_key: str | None = None, api_base: str | None = None) -> AsyncIterator[dict]:
    import litellm

    spec = get_model(model_id)
    if spec is None:
        raise ProviderError(f"Unknown model '{model_id}'")
    kwargs: dict = {"model": spec.litellm_model, "messages": messages, "stream": True, "stream_options": {"include_usage": True}, **_credentials(spec, api_key, api_base)}
    for key in ("temperature", "max_tokens"):
        if params.get(key) is not None:
            kwargs[key] = params[key]
    # top_p at its default of 1.0 is a no-op; sending it alongside temperature is rejected by Anthropic.
    if params.get("top_p") is not None and float(params["top_p"]) < 1.0:
        kwargs["top_p"] = params["top_p"]
    if spec.provider == "Anthropic" and "temperature" in kwargs and "top_p" in kwargs:
        kwargs.pop("top_p")
    litellm.drop_params = True

    started = time.perf_counter()
    tokens_in = tokens_out = tokens_cached = 0
    try:
        response = await litellm.acompletion(**kwargs)
        async for chunk in response:
            choices = getattr(chunk, "choices", None) or []
            if choices:
                delta = getattr(choices[0], "delta", None)
                text = getattr(delta, "content", None) if delta is not None else None
                if text:
                    yield {"type": "delta", "text": text}
            usage = getattr(chunk, "usage", None)
            if usage is not None:
                tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0)
                tokens_out = int(getattr(usage, "completion_tokens", 0) or 0)
                details = getattr(usage, "prompt_tokens_details", None)
                tokens_cached = int(getattr(details, "cached_tokens", 0) or 0) if details is not None else 0
    except Exception as exc:  # provider errors surface as a typed error event
        raise ProviderError(str(exc)[:500]) from exc

    cost = estimate_cost(model_id, tokens_in, tokens_out, tokens_cached)
    yield {"type": "usage", "usage": Usage(tokens_in, tokens_out, tokens_cached, cost, int((time.perf_counter() - started) * 1000))}


def stream_completion(model_id: str, messages: list[dict], params: dict, api_key: str | None = None, api_base: str | None = None) -> AsyncIterator[dict]:
    if settings.fake_llm:
        return _fake_stream(model_id, messages, params)
    return _litellm_stream(model_id, messages, params, api_key=api_key, api_base=api_base)


def _fake_complete(model_id: str, messages: list[dict]) -> tuple[str, Usage]:
    """Synchronous fake completion for agent nodes. Returns text that is useful for deterministic tests."""
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    spec = get_model(model_id)
    name = spec.name if spec else model_id
    text = f"[fake {name}] " + last_user[:400]
    tokens_in = max(8, sum(len(m["content"]) for m in messages) // 4)
    tokens_out = max(4, len(text) // 4)
    return text, Usage(tokens_in, tokens_out, 0, estimate_cost(model_id, tokens_in, tokens_out), 5)


def _fake_tool_calls(messages: list[dict], tools: list[dict]) -> list[dict]:
    """Pick the tool whose name shares a word with the request; fill required string arguments with the request text."""
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    words = set(re.findall(r"[a-z]+", last_user.lower()))
    for t in tools:
        fn = t.get("function", t)
        name = fn.get("name", "")
        if set(name.lower().replace("-", "_").split("_")) & words:
            schema = fn.get("parameters") or {}
            args = {k: (last_user[:200] if (v or {}).get("type") == "string" else 5) for k, v in (schema.get("properties") or {}).items() if k in (schema.get("required") or [])}
            return [{"id": "call_fake_1", "name": name, "arguments": args}]
    return []


def complete_with_tools(model_id: str, messages: list[dict], tools: list[dict], max_tokens: int = 1500, temperature: float = 0.2, api_key: str | None = None, api_base: str | None = None) -> tuple[str, list[dict], Usage]:
    """One model turn that may request tool calls. Returns (text, tool_calls, usage); tool_calls carry parsed JSON arguments."""
    if settings.fake_llm:
        calls = _fake_tool_calls(messages, tools)
        text, usage = _fake_complete(model_id, messages)
        return ("" if calls else text), calls, usage
    import litellm

    spec = get_model(model_id)
    if spec is None:
        raise ProviderError(f"Unknown model '{model_id}'")
    creds = _credentials(spec, api_key, api_base)
    litellm.drop_params = True
    started = time.perf_counter()
    try:
        response = litellm.completion(model=spec.litellm_model, messages=messages, tools=tools, tool_choice="auto", max_tokens=max_tokens, temperature=temperature, **creds)
    except Exception as exc:
        raise ProviderError(str(exc)[:500]) from exc
    msg = response.choices[0].message
    calls = []
    for tc in getattr(msg, "tool_calls", None) or []:
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        calls.append({"id": tc.id, "name": tc.function.name, "arguments": args})
    usage = getattr(response, "usage", None)
    tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0)
    tokens_out = int(getattr(usage, "completion_tokens", 0) or 0)
    return (msg.content or ""), calls, Usage(tokens_in, tokens_out, 0, estimate_cost(model_id, tokens_in, tokens_out), int((time.perf_counter() - started) * 1000))


def complete(model_id: str, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.2, api_key: str | None = None, api_base: str | None = None) -> tuple[str, Usage]:
    """Blocking completion used inside blueprint nodes. Raises ProviderError on provider failure."""
    if settings.fake_llm:
        return _fake_complete(model_id, messages)
    import litellm

    spec = get_model(model_id)
    if spec is None:
        raise ProviderError(f"Unknown model '{model_id}'")
    creds = _credentials(spec, api_key, api_base)
    litellm.drop_params = True
    started = time.perf_counter()
    try:
        response = litellm.completion(model=spec.litellm_model, messages=messages, max_tokens=max_tokens, temperature=temperature, **creds)
    except Exception as exc:
        raise ProviderError(str(exc)[:500]) from exc
    text = response.choices[0].message.content or ""
    usage = getattr(response, "usage", None)
    tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0)
    tokens_out = int(getattr(usage, "completion_tokens", 0) or 0)
    details = getattr(usage, "prompt_tokens_details", None)
    cached = int(getattr(details, "cached_tokens", 0) or 0) if details is not None else 0
    return text, Usage(tokens_in, tokens_out, cached, estimate_cost(model_id, tokens_in, tokens_out, cached), int((time.perf_counter() - started) * 1000))
