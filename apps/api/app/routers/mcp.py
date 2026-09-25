"""The playground's MCP endpoint and the personal access tokens that external clients use to reach it."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_user
from app.config import settings
from app.db import get_db
from app.mcp_server import client_config, handle_message
from app.models import ApiToken, User

router = APIRouter(tags=["mcp"])


class TokenBody(BaseModel):
    name: str = Field(min_length=2, max_length=80)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _payload(t: ApiToken) -> dict:
    return {"id": t.id, "name": t.name, "prefix": t.prefix, "created_at": t.created_at.isoformat(), "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None}


@router.get("/v1/tokens")
def list_tokens(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(ApiToken).where(ApiToken.user_id == user.id).order_by(ApiToken.created_at.desc())).all()
    return {"tokens": [_payload(t) for t in rows], "mcp_url": f"{settings.self_url}/mcp"}


@router.post("/v1/tokens", status_code=201)
def create_token(body: TokenBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """The token value is returned once and never stored."""
    raw = "pgk_" + secrets.token_urlsafe(32)
    t = ApiToken(user_id=user.id, name=body.name, prefix=raw[:10], token_hash=_hash(raw))
    db.add(t)
    db.commit()
    return {**_payload(t), "token": raw, "client_config": client_config(raw)}


@router.delete("/v1/tokens/{token_id}", status_code=204)
def revoke_token(token_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    t = db.get(ApiToken, token_id)
    if t is None or t.user_id != user.id:
        raise HTTPException(status_code=404, detail="Token not found")
    db.delete(t)
    db.commit()


def mcp_user(
    authorization: str = Header(default=""),
    x_internal_key: str = Header(default=""),
    x_user_id: str = Header(default=""),
    x_user_email: str = Header(default=""),
    x_user_name: str = Header(default=""),
    x_user_role: str = Header(default="explorer"),
    x_user_department: str = Header(default="General"),
    db: Session = Depends(get_db),
) -> User:
    """Bearer token for external clients; the web app's identity headers for the in-product connector."""
    if authorization.lower().startswith("bearer "):
        t = db.scalar(select(ApiToken).where(ApiToken.token_hash == _hash(authorization[7:].strip())))
        if t is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        t.last_used_at = datetime.now(UTC)
        db.commit()
        user = db.get(User, t.user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="Token owner no longer exists")
        return user
    return current_user(x_internal_key, x_user_id, x_user_email, x_user_name, x_user_role, x_user_department, db)


@router.post("/mcp")
async def mcp_endpoint(request: Request, user: User = Depends(mcp_user)) -> JSONResponse:
    try:
        body = await request.json()
    except ValueError:
        return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}, status_code=400)
    messages = body if isinstance(body, list) else [body]
    responses = [r for r in (handle_message(m, user) for m in messages if isinstance(m, dict)) if r]
    if not responses:
        return JSONResponse(None, status_code=202)
    return JSONResponse(responses if isinstance(body, list) else responses[0], headers={"mcp-session-id": f"pg-{user.id}"})


@router.get("/mcp")
def mcp_stream_not_supported() -> JSONResponse:
    """Server-initiated streams are not offered; clients use plain request and response, which the spec allows."""
    return JSONResponse({"detail": "This server responds to POST requests only"}, status_code=405)
