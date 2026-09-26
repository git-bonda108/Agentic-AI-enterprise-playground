"""Provider keys: the platform's own keys (environment, hidden) and each person's own keys (encrypted at rest).

Resolution order for a model call: the caller's personal key for that provider first; otherwise the platform key when the
admin scope allows it for that feature. Platform agents, the judge, canaries and the curator always use platform keys.
"""

from __future__ import annotations

import base64
import hashlib
import os
from datetime import UTC, datetime

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog import CATALOG
from app.config import settings
from app.models import AppSetting, ProviderKey, User

PROVIDERS: dict[str, dict] = {
    "Anthropic": {
        "env_key": "ANTHROPIC_API_KEY",
        "prefix": "sk-ant-",
        "key_page": "https://platform.claude.com/settings/keys",
        "docs": "https://platform.claude.com/docs/en/get-started",
        "pricing": "https://platform.claude.com/docs/en/about-claude/pricing",
    },
    "OpenAI": {
        "env_key": "OPENAI_API_KEY",
        "prefix": "sk-",
        "key_page": "https://platform.openai.com/api-keys",
        "docs": "https://developers.openai.com/api/docs/quickstart",
        "pricing": "https://developers.openai.com/api/docs/pricing",
    },
    "Google": {
        "env_key": "GEMINI_API_KEY",
        "prefix": "AIza",
        "key_page": "https://aistudio.google.com/apikey",
        "docs": "https://ai.google.dev/gemini-api/docs/quickstart",
        "pricing": "https://ai.google.dev/gemini-api/docs/pricing",
    },
    "DeepSeek": {
        "env_key": "DEEPSEEK_API_KEY",
        "prefix": "sk-",
        "key_page": "https://platform.deepseek.com/api_keys",
        "docs": "https://api-docs.deepseek.com/",
        "pricing": "https://api-docs.deepseek.com/quick_start/pricing",
    },
    "Azure OpenAI": {
        "env_key": "AZURE_API_KEY",
        "prefix": "",
        "key_page": "https://ai.azure.com/",
        "docs": "https://learn.microsoft.com/en-us/azure/ai-foundry/openai/quickstart",
        "pricing": "https://azure.microsoft.com/en-us/pricing/details/azure-openai/",
        "needs_base": True,
    },
    "Hugging Face": {
        "env_key": "HUGGINGFACE_API_KEY",
        "prefix": "hf_",
        "key_page": "https://huggingface.co/settings/tokens",
        "docs": "https://huggingface.co/docs/inference-providers",
        "pricing": "https://huggingface.co/docs/inference-providers/pricing",
    },
    "NVIDIA NIM": {
        "env_key": "NVIDIA_NIM_API_KEY",
        "prefix": "nvapi-",
        "key_page": "https://build.nvidia.com/settings/api-keys",
        "docs": "https://docs.api.nvidia.com/nim/",
        "pricing": "https://build.nvidia.com/explore/discover",
    },
    "Mistral": {
        "env_key": "MISTRAL_API_KEY",
        "prefix": "",
        "key_page": "https://console.mistral.ai/api-keys",
        "docs": "https://docs.mistral.ai/getting-started/quickstart/",
        "pricing": "https://mistral.ai/pricing/",
    },
    "xAI": {
        "env_key": "XAI_API_KEY",
        "prefix": "xai-",
        "key_page": "https://console.x.ai/",
        "docs": "https://docs.x.ai/developers/quickstart",
        "pricing": "https://docs.x.ai/developers/pricing",
    },
    "Groq": {
        "env_key": "GROQ_API_KEY",
        "prefix": "gsk_",
        "key_page": "https://console.groq.com/keys",
        "docs": "https://console.groq.com/docs/quickstart",
        "pricing": "https://groq.com/pricing",
    },
    "Cohere": {
        "env_key": "COHERE_API_KEY",
        "prefix": "",
        "key_page": "https://dashboard.cohere.com/api-keys",
        "docs": "https://docs.cohere.com/docs/get-started",
        "pricing": "https://cohere.com/pricing",
    },
}

# Features the product itself runs; these always use platform keys.
PLATFORM_FEATURES = {"platform", "eval", "canary", "curator"}
SCOPE_SETTING = "platform_key_scope"  # "all" (platform keys serve everyone) | "platform-only"


# ---------------------------------------------------------------- encryption ----------------------------------------------------------------


def _fernet() -> Fernet:
    raw = settings.key_encryption_key.strip()
    if not raw:
        # local convenience only; production requires an explicit key (see security.assert_safe_configuration)
        raw = base64.urlsafe_b64encode(
            hashlib.sha256(f"eap-keys:{settings.internal_key}".encode()).digest()
        ).decode()
    return Fernet(raw.encode())


def encrypt(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt(token: str) -> str | None:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        return None


# ---------------------------------------------------------------- settings ----------------------------------------------------------------


def key_scope(db: Session) -> str:
    row = db.get(AppSetting, SCOPE_SETTING)
    return (row.value or {}).get("scope", "all") if row else "all"


def set_key_scope(db: Session, scope: str) -> str:
    row = db.get(AppSetting, SCOPE_SETTING)
    if row is None:
        row = AppSetting(key=SCOPE_SETTING, value={"scope": scope})
        db.add(row)
    else:
        row.value = {"scope": scope}
    db.commit()
    return scope


# ---------------------------------------------------------------- personal keys ----------------------------------------------------------------


def personal_key_row(db: Session, user_id: str, provider: str) -> ProviderKey | None:
    return db.scalar(
        select(ProviderKey).where(ProviderKey.user_id == user_id, ProviderKey.provider == provider)
    )


def save_personal_key(
    db: Session, user: User, provider: str, secret: str, extra: dict | None = None
) -> ProviderKey:
    row = personal_key_row(db, user.id, provider)
    if row is None:
        row = ProviderKey(user_id=user.id, provider=provider)
        db.add(row)
    row.ciphertext = encrypt(secret)
    row.last4 = secret[-4:]
    row.extra = extra or {}
    db.commit()
    return row


def delete_personal_key(db: Session, user: User, provider: str) -> bool:
    row = personal_key_row(db, user.id, provider)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def platform_key(provider: str) -> str | None:
    env = PROVIDERS.get(provider, {}).get("env_key")
    return os.environ.get(env) if env else None


def resolve_key(
    db: Session, user_id: str | None, provider: str, feature: str = "chat"
) -> tuple[str | None, str, dict]:
    """Returns (secret, source, extra). Source is 'personal', 'platform', 'fake' or 'none'."""
    if settings.fake_llm:
        return None, "fake", {}
    if user_id and feature not in PLATFORM_FEATURES:
        row = personal_key_row(db, user_id, provider)
        if row is not None:
            secret = decrypt(row.ciphertext)
            if secret:
                row.last_used_at = datetime.now(UTC)
                db.commit()
                return secret, "personal", row.extra or {}
    if feature in PLATFORM_FEATURES or key_scope(db) == "all" or user_id is None:
        secret = platform_key(provider)
        if secret:
            return secret, "platform", {}
    return None, "none", {}


def available_providers(db: Session, user: User | None, feature: str = "chat") -> dict[str, str]:
    """Provider name to key source for what this caller may use right now."""
    names = {m.provider for m in CATALOG}
    if settings.fake_llm:
        return {n: "fake" for n in names}
    out: dict[str, str] = {}
    scope = key_scope(db)
    personal = (
        {
            r.provider
            for r in db.scalars(select(ProviderKey).where(ProviderKey.user_id == user.id)).all()
        }
        if user and feature not in PLATFORM_FEATURES
        else set()
    )
    for n in names:
        if n in personal:
            out[n] = "personal"
        elif platform_key(n) and (feature in PLATFORM_FEATURES or scope == "all" or user is None):
            out[n] = "platform"
    return out


def provider_status(db: Session, user: User) -> list[dict]:
    """What the key drawer shows: one row per provider with its source, links and model count."""
    scope = key_scope(db)
    rows = {
        r.provider: r
        for r in db.scalars(select(ProviderKey).where(ProviderKey.user_id == user.id)).all()
    }
    counts: dict[str, int] = {}
    for m in CATALOG:
        counts[m.provider] = counts.get(m.provider, 0) + 1
    out = []
    for name, meta in PROVIDERS.items():
        row = rows.get(name)
        platform = bool(platform_key(name))
        source = (
            "personal"
            if row
            else (
                "platform"
                if platform and scope == "all"
                else ("fake" if settings.fake_llm else "none")
            )
        )
        out.append(
            {
                "provider": name,
                "env_key": meta["env_key"],
                "key_page": meta["key_page"],
                "docs": meta["docs"],
                "pricing": meta["pricing"],
                "prefix": meta["prefix"],
                "needs_base": bool(meta.get("needs_base")),
                "models": counts.get(name, 0),
                "platform_configured": platform,
                "personal": {
                    "last4": row.last4,
                    "extra": row.extra or {},
                    "created_at": row.created_at.isoformat(),
                    "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
                }
                if row
                else None,
                "source": source,
                "usable": source != "none",
            }
        )
    return out
