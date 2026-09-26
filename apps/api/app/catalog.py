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
        """True when the platform's own key for this provider is present (or the fake provider is on)."""
        if settings.fake_llm:
            return True
        return bool(os.environ.get(self.env_key)) if self.env_key else False

    def platform_configured(self) -> bool:
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
    # NVIDIA NIM: the free developer endpoint (about 40 requests a minute) hosts Nemotron and 100+ open models. Production runs on NVIDIA AI Enterprise or self-hosted NIM.
    ModelSpec("nim-nemotron-3-super", "Nemotron 3 Super 120B", "NVIDIA NIM", "Workhorse", "nvidia_nim/nvidia/nemotron-3-super-120b-a12b", 0.0, 0.0, None, 262_144, ["Agents", "Tool calling", "Open weights"], "NVIDIA_NIM_API_KEY", "Free developer endpoint, rate limited; hybrid Mamba-Transformer MoE with 12B active parameters", "GA", "https://build.nvidia.com/explore/discover", ("text", "tools")),
    ModelSpec("nim-nemotron-3-nano", "Nemotron 3 Nano 30B", "NVIDIA NIM", "Economy", "nvidia_nim/nvidia/nemotron-3-nano-30b-a3b", 0.0, 0.0, None, 262_144, ["Sub-agents", "Fast", "Open weights"], "NVIDIA_NIM_API_KEY", "Free developer endpoint, rate limited; 3B active parameters", "GA", "https://build.nvidia.com/explore/discover", ("text", "tools")),
    ModelSpec("nim-nemotron-3-ultra", "Nemotron 3 Ultra 550B", "NVIDIA NIM", "Premium", "nvidia_nim/nvidia/nemotron-3-ultra-550b-a55b", 0.0, 0.0, None, 1_000_000, ["Reasoning", "Multi-step", "Open weights"], "NVIDIA_NIM_API_KEY", "Released June 2026; confirm the exact identifier on build.nvidia.com before relying on it", "Preview", "https://build.nvidia.com/explore/discover", ("text", "tools")),
    ModelSpec("nim-hermes-4-405b", "Hermes 4 405B (Nous Research)", "NVIDIA NIM", "Premium", "nvidia_nim/nousresearch/hermes-4-405b", 0.0, 0.0, None, 128_000, ["Agents", "Hermes Agent default family"], "NVIDIA_NIM_API_KEY", "Also served by the Nous Portal; confirm the identifier on build.nvidia.com", "Preview", "https://hermes-agent.nousresearch.com/docs/integrations/providers", ("text", "tools")),
    ModelSpec("nim-llama-3-3-70b", "Llama 3.3 70B (NIM)", "NVIDIA NIM", "Economy", "nvidia_nim/meta/llama-3.3-70b-instruct", 0.0, 0.0, None, 128_000, ["Open weights", "General"], "NVIDIA_NIM_API_KEY", "Free developer endpoint, rate limited", "GA", "https://build.nvidia.com/explore/discover", ("text", "tools")),
    ModelSpec("nim-qwen3-235b", "Qwen3 235B (NIM)", "NVIDIA NIM", "Workhorse", "nvidia_nim/qwen/qwen3-235b-a22b", 0.0, 0.0, None, 128_000, ["Open weights", "Multilingual", "Reasoning"], "NVIDIA_NIM_API_KEY", "Free developer endpoint, rate limited", "GA", "https://build.nvidia.com/explore/discover", ("text", "tools")),
    # Mistral, prices from mistral.ai/pricing as of September 2026
    ModelSpec("mistral-medium-3-5", "Mistral Medium 3.5", "Mistral", "Premium", "mistral/mistral-medium-latest", 1.50, 7.50, None, 128_000, ["Flagship", "Coding", "EU hosted"], "MISTRAL_API_KEY", "", "GA", "https://mistral.ai/pricing/", ("text", "tools", "vision")),
    ModelSpec("mistral-large-3", "Mistral Large 3", "Mistral", "Workhorse", "mistral/mistral-large-latest", 0.50, 1.50, None, 128_000, ["Everyday tasks", "EU hosted"], "MISTRAL_API_KEY", "", "GA", "https://mistral.ai/pricing/", ("text", "tools")),
    ModelSpec("mistral-small-4", "Mistral Small 4", "Mistral", "Economy", "mistral/mistral-small-latest", 0.15, 0.60, None, 128_000, ["Budget", "Fast"], "MISTRAL_API_KEY", "", "GA", "https://mistral.ai/pricing/", ("text", "tools")),
    ModelSpec("codestral", "Codestral", "Mistral", "Economy", "mistral/codestral-latest", 0.30, 0.90, None, 256_000, ["Code", "Fill in the middle"], "MISTRAL_API_KEY", "", "GA", "https://mistral.ai/pricing/", ("text",)),
    # xAI, prices from docs.x.ai as of September 2026 (long-context rate applies above 200K tokens)
    ModelSpec("grok-4-7", "Grok 4.7", "xAI", "Premium", "xai/grok-4.7", 2.0, 6.0, 0.50, 500_000, ["Flagship", "Agents", "Coding"], "XAI_API_KEY", "Prompts over 200K tokens bill at 4.00 in and 12.00 out", "GA", "https://docs.x.ai/developers/pricing", ("text", "tools", "vision")),
    ModelSpec("grok-4-3", "Grok 4.3", "xAI", "Workhorse", "xai/grok-4.3", 1.25, 2.50, 0.20, 256_000, ["Everyday tasks"], "XAI_API_KEY", "", "GA", "https://docs.x.ai/developers/pricing", ("text", "tools")),
    # Groq, prices from groq.com pricing as of September 2026
    ModelSpec("groq-gpt-oss-120b", "GPT-OSS 120B (Groq)", "Groq", "Economy", "groq/openai/gpt-oss-120b", 0.15, 0.60, None, 131_072, ["Fastest inference", "Open weights"], "GROQ_API_KEY", "", "GA", "https://groq.com/pricing", ("text", "tools")),
    ModelSpec("groq-gpt-oss-20b", "GPT-OSS 20B (Groq)", "Groq", "Economy", "groq/openai/gpt-oss-20b", 0.075, 0.30, None, 131_072, ["Cheapest", "Fastest inference"], "GROQ_API_KEY", "", "GA", "https://groq.com/pricing", ("text", "tools")),
    # Cohere
    ModelSpec("cohere-command-a", "Command A", "Cohere", "Workhorse", "cohere/command-a-03-2025", 2.50, 10.0, None, 256_000, ["Enterprise RAG", "Multilingual"], "COHERE_API_KEY", "", "GA", "https://cohere.com/pricing", ("text", "tools")),
]

BY_ID = {m.id: m for m in CATALOG}


def get_model(model_id: str) -> ModelSpec | None:
    return BY_ID.get(model_id)


def catalog_payload(providers: dict[str, str] | None = None) -> list[dict]:
    """`providers` maps provider name to the key source available to the caller ("personal" or "platform")."""
    out = []
    for m in CATALOG:
        d = asdict(m)
        d["capabilities"] = list(m.capabilities)
        if providers is None:
            d["available"] = m.available()
            d["key_source"] = "platform" if m.platform_configured() else ("fake" if settings.fake_llm else "none")
        else:
            d["available"] = m.provider in providers
            d["key_source"] = providers.get(m.provider, "none")
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
