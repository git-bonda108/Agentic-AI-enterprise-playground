"""Model catalog: the price sheet the ledger uses. Prices are USD per 1M tokens."""

import os
from dataclasses import asdict, dataclass, field

from app.config import settings


@dataclass(frozen=True)
class ModelSpec:
    id: str
    name: str
    provider: str
    tier: str  # Frontier | Premium | Workhorse | Economy
    litellm_model: str
    input_per_m: float
    output_per_m: float
    cached_input_per_m: float | None
    context: int
    tags: list[str] = field(default_factory=list)
    env_key: str = ""
    notes: str = ""
    lifecycle: str = "GA"
    docs_url: str = ""
    capabilities: tuple[str, ...] = ("text", "tools")

    def available(self) -> bool:
        if settings.fake_llm:
            return True
        return bool(os.environ.get(self.env_key)) if self.env_key else False


CATALOG: list[ModelSpec] = [
    ModelSpec("claude-fable-5-1", "Claude Fable 5.1", "Anthropic", "Frontier", "anthropic/claude-fable-5-1", 10.0, 50.0, 0.25, 1_000_000, ["Most capable", "Research", "Multi-day tasks"], "ANTHROPIC_API_KEY", "", "GA", "https://platform.claude.com/docs/en/about-claude/pricing", ("text", "tools", "vision", "caching")),
    ModelSpec("claude-opus-5-5", "Claude Opus 5.5", "Anthropic", "Premium", "anthropic/claude-opus-5-5", 4.0, 20.0, 0.20, 1_000_000, ["Complex projects", "Agents", "Coding"], "ANTHROPIC_API_KEY", "", "GA", "https://platform.claude.com/docs/en/about-claude/pricing", ("text", "tools", "vision", "caching")),
    ModelSpec("claude-opus-5", "Claude Opus 5", "Anthropic", "Premium", "anthropic/claude-opus-5", 5.0, 25.0, 0.50, 1_000_000, ["Complex projects", "Agents"], "ANTHROPIC_API_KEY", "", "GA", "https://platform.claude.com/docs/en/about-claude/pricing", ("text", "tools", "vision", "caching")),
    ModelSpec("claude-sonnet-5", "Claude Sonnet 5", "Anthropic", "Workhorse", "anthropic/claude-sonnet-5", 2.0, 10.0, 0.20, 1_000_000, ["Everyday tasks", "Writing", "Cost-efficient"], "ANTHROPIC_API_KEY", "", "GA", "https://platform.claude.com/docs/en/about-claude/pricing", ("text", "tools", "vision", "caching")),
    ModelSpec("claude-haiku-4-5", "Claude Haiku 4.5", "Anthropic", "Economy", "anthropic/claude-haiku-4-5", 1.0, 5.0, 0.10, 200_000, ["Fastest", "Classification", "High volume"], "ANTHROPIC_API_KEY", "", "GA", "https://platform.claude.com/docs/en/about-claude/pricing", ("text", "tools", "vision", "caching")),
    ModelSpec("gpt-5.6-sol", "GPT-5.6 Sol", "OpenAI", "Frontier", "openai/gpt-5.6-sol", 5.0, 30.0, 0.50, 400_000, ["Flagship", "Reasoning"], "OPENAI_API_KEY", "", "GA", "https://developers.openai.com/api/docs/pricing", ("text", "tools", "vision", "caching")),
    ModelSpec("gpt-5.6-terra", "GPT-5.6 Terra", "OpenAI", "Workhorse", "openai/gpt-5.6-terra", 2.0, 12.0, 0.20, 400_000, ["Everyday tasks", "Tool use"], "OPENAI_API_KEY", "", "GA", "https://developers.openai.com/api/docs/pricing", ("text", "tools", "vision", "caching")),
    ModelSpec("gpt-5.6-luna", "GPT-5.6 Luna", "OpenAI", "Economy", "openai/gpt-5.6-luna", 0.20, 1.20, 0.02, 400_000, ["Budget", "High volume"], "OPENAI_API_KEY", "", "GA", "https://developers.openai.com/api/docs/pricing", ("text", "tools", "vision", "caching")),
    ModelSpec("gpt-5-nano", "GPT-5 nano", "OpenAI", "Economy", "openai/gpt-5-nano", 0.05, 0.40, 0.005, 400_000, ["Cheapest", "Classification"], "OPENAI_API_KEY", "", "GA", "https://developers.openai.com/api/docs/pricing", ("text", "tools", "vision", "caching")),
    ModelSpec("gemini-2.5-pro", "Gemini 2.5 Pro", "Google", "Premium", "gemini/gemini-2.5-pro", 2.0, 12.0, None, 1_000_000, ["Long context", "Multimodal"], "GEMINI_API_KEY", "Price for prompts up to 200K tokens", "GA", "https://ai.google.dev/gemini-api/docs/pricing", ("text", "tools", "vision")),
    ModelSpec("gemini-2.5-flash", "Gemini 2.5 Flash", "Google", "Economy", "gemini/gemini-2.5-flash", 0.15, 1.25, None, 1_000_000, ["Fast", "Multimodal"], "GEMINI_API_KEY", "", "GA", "https://ai.google.dev/gemini-api/docs/pricing", ("text", "tools", "vision")),
    ModelSpec("deepseek-v4-pro", "DeepSeek V4 Pro", "DeepSeek", "Workhorse", "deepseek/deepseek-v4-pro", 1.74, 3.48, None, 128_000, ["Reasoning", "Open weights"], "DEEPSEEK_API_KEY", "", "GA", "https://deepseek.ai/pricing", ("text", "tools")),
    ModelSpec("deepseek-v4-flash", "DeepSeek V4 Flash", "DeepSeek", "Economy", "deepseek/deepseek-v4-flash", 0.14, 0.28, None, 128_000, ["Lowest cost", "High volume"], "DEEPSEEK_API_KEY", "", "GA", "https://deepseek.ai/pricing", ("text", "tools")),
    ModelSpec("azure-gpt-5.6-terra", "GPT-5.6 Terra (Azure)", "Azure OpenAI", "Workhorse", "azure/gpt-5.6-terra", 2.0, 12.0, 0.20, 400_000, ["In your tenant"], "AZURE_API_KEY", "Deploy the model in Foundry and set AZURE_API_BASE", "GA", "https://azure.microsoft.com/en-us/pricing/details/azure-openai/", ("text", "tools", "vision", "caching")),
    ModelSpec("hf-llama-3-3-70b", "Llama 3.3 70B (Hugging Face)", "Hugging Face", "Economy", "huggingface/meta-llama/Llama-3.3-70B-Instruct", 0.26, 0.26, None, 128_000, ["Open weights"], "HUGGINGFACE_API_KEY", "", "Preview", "https://huggingface.co/docs/inference-providers", ("text",)),
]

BY_ID = {m.id: m for m in CATALOG}


def get_model(model_id: str) -> ModelSpec | None:
    return BY_ID.get(model_id)


def catalog_payload() -> list[dict]:
    out = []
    for m in CATALOG:
        d = asdict(m)
        d["capabilities"] = list(m.capabilities)
        d["available"] = m.available()
        out.append(d)
    return out


def estimate_cost(model_id: str, tokens_in: int, tokens_out: int, tokens_cached: int = 0) -> float:
    """USD cost for a call, from the catalog price sheet. Cached tokens are billed at the cached rate."""
    spec = get_model(model_id)
    if spec is None:
        return 0.0
    uncached_in = max(tokens_in - tokens_cached, 0)
    cached_rate = spec.cached_input_per_m if spec.cached_input_per_m is not None else spec.input_per_m
    cost = (
        uncached_in / 1_000_000 * spec.input_per_m
        + tokens_cached / 1_000_000 * cached_rate
        + tokens_out / 1_000_000 * spec.output_per_m
    )
    return round(cost, 8)
