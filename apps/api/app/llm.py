"""Streaming completions through LiteLLM, with a deterministic fake provider for tests."""

import asyncio
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


async def _litellm_stream(model_id: str, messages: list[dict], params: dict) -> AsyncIterator[dict]:
    import litellm

    spec = get_model(model_id)
    if spec is None:
        raise ProviderError(f"Unknown model '{model_id}'")
    if not spec.available():
        raise ProviderError(f"{spec.provider} is not configured. Set {spec.env_key} to enable {spec.name}.")

    kwargs: dict = {"model": spec.litellm_model, "messages": messages, "stream": True, "stream_options": {"include_usage": True}}
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


def stream_completion(model_id: str, messages: list[dict], params: dict) -> AsyncIterator[dict]:
    if settings.fake_llm:
        return _fake_stream(model_id, messages, params)
    return _litellm_stream(model_id, messages, params)


def _fake_complete(model_id: str, messages: list[dict]) -> tuple[str, Usage]:
    """Synchronous fake completion for agent nodes. Returns text that is useful for deterministic tests."""
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    spec = get_model(model_id)
    name = spec.name if spec else model_id
    text = f"[fake {name}] " + last_user[:400]
    tokens_in = max(8, sum(len(m["content"]) for m in messages) // 4)
    tokens_out = max(4, len(text) // 4)
    return text, Usage(tokens_in, tokens_out, 0, estimate_cost(model_id, tokens_in, tokens_out), 5)


def complete(model_id: str, messages: list[dict], max_tokens: int = 2048, temperature: float = 0.2) -> tuple[str, Usage]:
    """Blocking completion used inside blueprint nodes. Raises ProviderError on provider failure."""
    if settings.fake_llm:
        return _fake_complete(model_id, messages)
    import litellm

    spec = get_model(model_id)
    if spec is None:
        raise ProviderError(f"Unknown model '{model_id}'")
    if not spec.available():
        raise ProviderError(f"{spec.provider} is not configured. Set {spec.env_key} to enable {spec.name}.")
    litellm.drop_params = True
    started = time.perf_counter()
    try:
        response = litellm.completion(model=spec.litellm_model, messages=messages, max_tokens=max_tokens, temperature=temperature)
    except Exception as exc:
        raise ProviderError(str(exc)[:500]) from exc
    text = response.choices[0].message.content or ""
    usage = getattr(response, "usage", None)
    tokens_in = int(getattr(usage, "prompt_tokens", 0) or 0)
    tokens_out = int(getattr(usage, "completion_tokens", 0) or 0)
    details = getattr(usage, "prompt_tokens_details", None)
    cached = int(getattr(details, "cached_tokens", 0) or 0) if details is not None else 0
    return text, Usage(tokens_in, tokens_out, cached, estimate_cost(model_id, tokens_in, tokens_out, cached), int((time.perf_counter() - started) * 1000))
