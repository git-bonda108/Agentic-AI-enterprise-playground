from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import current_user
from app.catalog import catalog_payload
from app.db import get_db
from app.governance import allowed_model_ids, policy_for
from app.keys import available_providers, key_scope
from app.models import User

router = APIRouter(prefix="/v1/models", tags=["models"])


@router.get("")
def list_models(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    providers = available_providers(db, user, "chat")
    models = catalog_payload(providers)
    allowed = allowed_model_ids(db, user.role)
    for m in models:
        m["allowed"] = m["id"] in allowed
    policy = policy_for(db, user.role)
    return {
        "models": models, "available": sum(1 for m in models if m["available"]), "smart_enabled": policy.smart_enabled, "max_tokens": policy.max_tokens,
        "providers": providers, "key_scope": key_scope(db),
    }
