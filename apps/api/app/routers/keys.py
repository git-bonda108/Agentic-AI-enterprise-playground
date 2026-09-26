from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import current_user
from app.catalog import CATALOG
from app.db import get_db
from app.keys import (
    PROVIDERS,
    delete_personal_key,
    key_scope,
    provider_status,
    resolve_key,
    save_personal_key,
    set_key_scope,
)
from app.llm import ProviderError, complete
from app.models import User
from app.routers.admin import require_admin

router = APIRouter(prefix="/v1/keys", tags=["keys"])


class KeyBody(BaseModel):
    key: str = Field(min_length=8, max_length=512)
    api_base: str | None = Field(default=None, max_length=300)


class ScopeBody(BaseModel):
    scope: str = Field(pattern="^(all|platform-only)$")


@router.get("")
def list_keys(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    scope = key_scope(db)
    return {
        "providers": provider_status(db, user),
        "scope": scope,
        "scope_note": "Platform keys serve everyone"
        if scope == "all"
        else "Platform keys serve only the product's own agents; people bring their own keys",
    }


@router.put("/{provider}")
def put_key(
    provider: str, body: KeyBody, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    meta = PROVIDERS.get(provider)
    if meta is None:
        raise HTTPException(status_code=404, detail="Unknown provider")
    secret = body.key.strip()
    if meta["prefix"] and not secret.startswith(meta["prefix"]):
        raise HTTPException(status_code=400, detail=f"{provider} keys start with {meta['prefix']}")
    if meta.get("needs_base") and not body.api_base:
        raise HTTPException(
            status_code=400, detail=f"{provider} also needs the endpoint URL (api base)"
        )
    row = save_personal_key(
        db, user, provider, secret, {"api_base": body.api_base} if body.api_base else {}
    )
    return {"provider": provider, "last4": row.last4, "source": "personal"}


@router.delete("/{provider}", status_code=204)
def remove_key(
    provider: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> None:
    if not delete_personal_key(db, user, provider):
        raise HTTPException(status_code=404, detail="No personal key for this provider")


@router.post("/{provider}/test")
def test_key(
    provider: str, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    """One tiny completion on the cheapest model of the provider, with whichever key would be used for you."""
    spec = min(
        (m for m in CATALOG if m.provider == provider),
        key=lambda m: m.input_per_m + m.output_per_m,
        default=None,
    )
    if spec is None:
        raise HTTPException(status_code=404, detail="No model for this provider")
    secret, source, extra = resolve_key(db, user.id, provider, "chat")
    if source == "none":
        return {
            "ok": False,
            "source": source,
            "model": spec.id,
            "error": "No key available. Add yours or ask an admin to enable platform keys.",
        }
    try:
        text, usage = complete(
            spec.id,
            [{"role": "user", "content": "Reply with the single word OK."}],
            max_tokens=5,
            temperature=0.0,
            api_key=secret,
            api_base=extra.get("api_base"),
        )
    except ProviderError as exc:
        return {"ok": False, "source": source, "model": spec.id, "error": str(exc)[:300]}
    return {
        "ok": True,
        "source": source,
        "model": spec.id,
        "reply": text.strip()[:40],
        "cost_usd": usage.cost_usd,
    }


@router.put("/admin/scope")
def put_scope(
    body: ScopeBody, _: User = Depends(require_admin), db: Session = Depends(get_db)
) -> dict:
    return {"scope": set_key_scope(db, body.scope)}
