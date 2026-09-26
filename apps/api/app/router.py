"""Smart routing: a deterministic classifier picks a cost tier, then the cheapest allowed model in that tier."""

import re
from dataclasses import dataclass

from app.catalog import CATALOG, ModelSpec, estimate_cost, get_model

SMART = "smart"

TIER_CANDIDATES: dict[str, list[str]] = {
    "Economy": ["claude-haiku-4-5", "gpt-5.6-luna", "deepseek-v4-flash", "gemini-2.5-flash", "gpt-5-nano", "mistral-small-4", "groq-gpt-oss-20b", "nim-nemotron-3-nano"],
    "Workhorse": ["claude-sonnet-5", "gpt-5.6-terra", "deepseek-v4-pro", "azure-gpt-5.6-terra", "mistral-large-3", "grok-4-3", "nim-nemotron-3-super"],
    "Premium": ["claude-opus-5-5", "gpt-5.6-sol", "claude-opus-5", "gemini-2.5-pro", "grok-4-7", "mistral-medium-3-5"],
}
BASELINE_TIER = "Premium"

PREMIUM_WORDS = (
    "prove", "derive", "architecture", "architect", "design a system", "multi-step", "step by step", "legal", "contract",
    "compliance", "regulatory", "refactor", "debug", "root cause", "optimi", "trade-off", "tradeoff", "strategy",
    "security review", "threat model", "migrat", "comprehensive", "in depth", "in-depth", "analy", "evaluate",
    "compare and contrast", "research", "proposal", "specification", "spec ", "implementation plan", "audit",
    "reconcile", "forecast", "simulate", "why does", "explain the reasoning", "critique", "review this",
)
ECONOMY_WORDS = (
    "translate", "classify", "categori", "extract", "yes or no", "true or false", "what is the capital", "define ",
    "one word", "one sentence", "one line", "rewrite", "fix grammar", "fix the grammar", "proofread", "convert",
    "format", "tag ", "sentiment", "spell", "uppercase", "lowercase", "shorten", "tl;dr", "tldr", "list three",
    "list 3", "give me 3", "give me three", "synonym", "antonym", "how do you say", "what day", "abbreviat",
)


@dataclass
class RouteDecision:
    tier: str
    model: str
    reason: str
    baseline_model: str
    est_cost_usd: float
    est_baseline_cost_usd: float
    est_tokens_in: int
    est_tokens_out: int

    @property
    def est_savings_pct(self) -> float:
        if self.est_baseline_cost_usd <= 0:
            return 0.0
        return round((1 - self.est_cost_usd / self.est_baseline_cost_usd) * 100, 1)


def classify(prompt: str) -> tuple[str, str]:
    """Return (tier, reason) for a prompt. Cheap, deterministic, explainable."""
    text = prompt.strip()
    low = text.lower()
    length = len(text)
    code_lines = sum(1 for line in text.splitlines() if re.match(r"^\s*(def |class |import |from |const |let |function |public |private |#include|SELECT |{|})", line))
    questions = low.count("?")
    premium_hits = [w for w in PREMIUM_WORDS if w in low]
    economy_hits = [w for w in ECONOMY_WORDS if w in low]

    score = len(premium_hits) * 2
    if length > 1500:
        score += 2
    if code_lines > 20:
        score += 2
    if questions > 2:
        score += 1

    if score >= 3:
        why = premium_hits[:2] or (["long prompt"] if length > 1500 else ["large code block"])
        return "Premium", f"Deep reasoning signals: {', '.join(why)}"
    if economy_hits and score == 0 and length < 400:
        return "Economy", f"Simple task: {economy_hits[0].strip()}"
    if length < 60 and score == 0 and questions <= 1 and not economy_hits:
        return "Economy", "Very short prompt"
    return "Workhorse", "General task, balanced quality and cost"


def first_available(tier: str, allowed: set[str] | None = None, providers: set[str] | None = None) -> ModelSpec | None:
    """`providers` limits availability to the caller's usable providers (personal or platform keys); None means platform keys."""

    def usable(spec: ModelSpec) -> bool:
        return (spec.provider in providers) if providers is not None else spec.available()

    for model_id in TIER_CANDIDATES.get(tier, []):
        spec = get_model(model_id)
        if spec and usable(spec) and (allowed is None or model_id in allowed):
            return spec
    for spec in CATALOG:  # fall back to any usable model of that tier
        if spec.tier == tier and usable(spec) and (allowed is None or spec.id in allowed):
            return spec
    return None


def route(prompt: str, allowed: set[str] | None = None, providers: set[str] | None = None) -> RouteDecision | None:
    tier, reason = classify(prompt)
    order = {"Economy": ["Economy", "Workhorse", "Premium"], "Workhorse": ["Workhorse", "Economy", "Premium"], "Premium": ["Premium", "Workhorse", "Economy"]}[tier]
    chosen = None
    for t in order:
        chosen = first_available(t, allowed, providers)
        if chosen:
            tier = t
            break
    if chosen is None:
        return None
    baseline = first_available(BASELINE_TIER, None, providers) or first_available(BASELINE_TIER) or chosen
    tokens_in = max(16, len(prompt) // 4 + 24)
    tokens_out = 350 if tier == "Economy" else 600 if tier == "Workhorse" else 900
    return RouteDecision(
        tier=tier, model=chosen.id, reason=reason, baseline_model=baseline.id,
        est_cost_usd=estimate_cost(chosen.id, tokens_in, tokens_out),
        est_baseline_cost_usd=estimate_cost(baseline.id, tokens_in, tokens_out),
        est_tokens_in=tokens_in, est_tokens_out=tokens_out,
    )
