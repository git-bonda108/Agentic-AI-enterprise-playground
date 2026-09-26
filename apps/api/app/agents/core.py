"""Blueprint primitives: manifests, the run context every node uses, and metered LLM steps."""

from __future__ import annotations

import json
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TypedDict

from app.catalog import get_model
from app.db import SessionLocal
from app.llm import ProviderError, complete, complete_with_tools
from app.models import Run, UsageEvent
from app.router import first_available


class RunState(TypedDict, total=False):
    """Shared state shape for every blueprint graph. Blueprints add their own keys under `data`."""

    input: dict
    data: dict
    output: dict | None
    steps: list[dict]
    review: dict | None
    error: str | None


TIER_FALLBACK = {"Economy": ["Economy", "Workhorse", "Premium"], "Workhorse": ["Workhorse", "Economy", "Premium"], "Premium": ["Premium", "Workhorse", "Economy"]}


@dataclass
class RunContext:
    """Everything a node needs that is not part of graph state: identity, metering, model resolution."""

    run_id: str
    blueprint_id: str
    user_id: str
    allowed_models: set[str] | None = None
    providers: dict[str, str] | None = None  # provider -> key source usable by this run; None means platform keys only
    feature: str = "agent"  # "agent" for people's runs; "canary" / "platform" always resolve to platform keys
    lock: threading.Lock = field(default_factory=threading.Lock)

    def resolve_model(self, tier: str) -> str:
        usable = set(self.providers) if self.providers is not None else None
        for t in TIER_FALLBACK.get(tier, ["Workhorse", "Economy", "Premium"]):
            spec = first_available(t, self.allowed_models, usable)
            if spec:
                return spec.id
        raise ProviderError("No model with a usable key is available for this run. Add a provider key from the Keys drawer, or ask an admin to enable platform keys.")

    def _credentials(self, model_id: str) -> tuple[dict, str]:
        """(kwargs for the LLM call, key source) for the resolved model."""
        from app.keys import resolve_key

        spec = get_model(model_id)
        if spec is None:
            return {}, "none"
        with SessionLocal() as db:
            secret, source, extra = resolve_key(db, self.user_id, spec.provider, self.feature)
        if source == "none":
            raise ProviderError(f"No {spec.provider} key is available for {spec.name}. Add your own key from the Keys drawer.")
        return ({"api_key": secret, "api_base": extra.get("api_base")} if secret else {}), source

    def llm(self, tier: str, system: str, user: str, *, max_tokens: int = 1500, temperature: float = 0.2, json_mode: bool = False) -> str:
        """One metered model call. Cost lands on the ledger and on the run."""
        model_id = self.resolve_model(tier)
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        if json_mode:
            messages[0]["content"] += " Respond with valid JSON only, no prose."
        creds, source = self._credentials(model_id)
        text, usage = complete(model_id, messages, max_tokens=max_tokens, temperature=temperature, **creds)
        self._meter(model_id, usage, source)
        return text

    def llm_tools(self, tier: str, system: str, user: str, tools: list[dict], *, max_tokens: int = 1500) -> tuple[str, list[dict]]:
        """A metered model turn that may ask for tool calls (OpenAI-style tool specs)."""
        model_id = self.resolve_model(tier)
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        creds, source = self._credentials(model_id)
        text, calls, usage = complete_with_tools(model_id, messages, tools, max_tokens=max_tokens, **creds)
        self._meter(model_id, usage, source)
        return text, calls

    def _meter(self, model_id: str, usage, key_source: str = "platform") -> None:
        spec = get_model(model_id)
        with self.lock, SessionLocal() as db:
            db.add(UsageEvent(
                user_id=self.user_id, feature="agent", model=model_id, provider=spec.provider if spec else "unknown",
                tokens_in=usage.tokens_in, tokens_out=usage.tokens_out, tokens_cached=usage.tokens_cached, cost_usd=usage.cost_usd,
                latency_ms=usage.latency_ms, status="ok", run_id=self.run_id, blueprint_id=self.blueprint_id, key_source=key_source,
            ))
            run = db.get(Run, self.run_id)
            if run is not None:
                run.cost_usd = round(run.cost_usd + usage.cost_usd, 8)
                run.tokens_in += usage.tokens_in
                run.tokens_out += usage.tokens_out
            db.commit()


def parse_json(text: str, fallback: Any) -> Any:
    """Best-effort JSON extraction from a model reply (handles code fences and leading prose)."""
    candidate = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", candidate, re.DOTALL)
    if fence:
        candidate = fence.group(1).strip()
    for attempt in (candidate, candidate[candidate.find("{") :], candidate[candidate.find("[") :]):
        try:
            return json.loads(attempt)
        except (ValueError, TypeError):
            continue
    return fallback


def step(state: RunState, node: str, summary: str, detail: dict | None = None, kind: str = "tool") -> dict:
    """Append a step record. Returned dict is merged into state by the caller."""
    record = {"node": node, "kind": kind, "summary": summary[:400], "detail": detail or {}, "at": datetime.now(UTC).isoformat(), "ms": 0}
    return {"steps": [*state.get("steps", []), record]}


def timed(fn: Callable[[], Any]) -> tuple[Any, int]:
    started = time.perf_counter()
    result = fn()
    return result, int((time.perf_counter() - started) * 1000)


@dataclass
class Blueprint:
    id: str
    name: str
    family: str
    pattern: str
    summary: str
    description: str
    tiers: dict[str, str]  # step role -> tier, shown to users as the model policy
    graph: dict  # nodes, edges, columns for the viewer
    samples: list[dict]  # named sample inputs
    datasets: list[str]
    flavors: list[str]
    review_gates: list[str]
    dashboard: list[str]
    links: dict[str, str]
    build: Callable[[Any], Any]  # (checkpointer) -> compiled graph
    input_schema: dict = field(default_factory=dict)
    batch: int = 3

    def manifest(self) -> dict:
        return {
            "id": self.id, "name": self.name, "family": self.family, "pattern": self.pattern, "summary": self.summary,
            "description": self.description, "tiers": self.tiers, "graph": self.graph, "samples": self.samples,
            "datasets": self.datasets, "flavors": self.flavors, "review_gates": self.review_gates, "dashboard": self.dashboard,
            "links": self.links, "input_schema": self.input_schema, "batch": self.batch,
        }


REGISTRY: dict[str, Blueprint] = {}


def register(bp: Blueprint) -> Blueprint:
    REGISTRY[bp.id] = bp
    return bp
