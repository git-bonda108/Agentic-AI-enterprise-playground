from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import current_user
from app.connectors import (
    CATEGORIES,
    McpClient,
    McpError,
    payload,
    probe,
    sync_registry,
    tool_result_text,
)
from app.db import get_db
from app.models import Connector, User
from app.routers.admin import require_admin

router = APIRouter(prefix="/v1/connectors", tags=["connectors"])


class ApprovalBody(BaseModel):
    approval: str = Field(pattern="^(pending|approved|blocked)$")
    note: str = Field(default="", max_length=400)


class ProbeBody(BaseModel):
    headers: dict[str, str] = Field(default_factory=dict)


class CallBody(BaseModel):
    tool: str
    arguments: dict = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)


@router.get("")
def list_connectors(
    q: str = Query(default=""), category: str = Query(default=""), transport: str = Query(default=""), approval: str = Query(default=""),
    publisher: str = Query(default=""), limit: int = Query(default=60, le=200), offset: int = Query(default=0, ge=0),
    _: User = Depends(current_user), db: Session = Depends(get_db),
) -> dict:
    stmt = select(Connector)
    if q:
        needle = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(Connector.id).like(needle) | func.lower(Connector.title).like(needle) | func.lower(Connector.description).like(needle))
    if category:
        stmt = stmt.where(Connector.category == category)
    if transport:
        stmt = stmt.where(Connector.transport == transport)
    if approval:
        stmt = stmt.where(Connector.approval == approval)
    if publisher:
        stmt = stmt.where(Connector.publisher == publisher)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    # approved first, then the strongest signals, then name
    rows = db.scalars(stmt.order_by((Connector.approval == "approved").desc(), Connector.signals.desc(), Connector.title).offset(offset).limit(limit)).all()
    return {"connectors": [payload(c) for c in rows], "total": total, "offset": offset, "limit": limit}


@router.get("/stats")
def connector_stats(_: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    total = db.scalar(select(func.count(Connector.id))) or 0
    by_approval = {k: v for k, v in db.execute(select(Connector.approval, func.count()).group_by(Connector.approval)).all()}
    by_transport = {k: v for k, v in db.execute(select(Connector.transport, func.count()).group_by(Connector.transport)).all()}
    by_category = {k: v for k, v in db.execute(select(Connector.category, func.count()).group_by(Connector.category).order_by(func.count().desc())).all()}
    newest = db.scalar(select(func.max(Connector.registry_updated_at)))
    return {"total": total, "by_approval": by_approval, "by_transport": by_transport, "by_category": by_category, "categories": [c[0] for c in CATEGORIES] + ["Other"], "registry_newest": newest}


@router.get("/featured")
def featured(_: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """The shelf at the top of the marketplace: the playground itself, then admin-approved servers by signal strength."""
    from app.connectors import PLAYGROUND_CONNECTOR_ID
    from app.mcp_clients import DIRECTORIES

    own = db.get(Connector, PLAYGROUND_CONNECTOR_ID)
    approved = db.scalars(select(Connector).where(Connector.approval == "approved", Connector.id != PLAYGROUND_CONNECTOR_ID).order_by(Connector.signals.desc(), Connector.title).limit(11)).all()
    rows = ([own] if own else []) + list(approved)
    return {"featured": [payload(c) for c in rows], "directories": DIRECTORIES}


@router.get("/{connector_id:path}/clients")
def clients(connector_id: str, _: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Configuration for every supported client, in that client's own format."""
    from app.mcp_clients import client_configs

    c = db.get(Connector, connector_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Unknown connector")
    return {"connector": payload(c), "clients": client_configs(payload(c))}


@router.post("/sync")
def sync(_: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    try:
        return sync_registry(db)
    except Exception as exc:  # network failures surface as a readable message, not a 500
        raise HTTPException(status_code=502, detail=f"Registry sync failed: {str(exc)[:200]}") from exc


def _get(connector_id: str, db: Session) -> Connector:
    c = db.get(Connector, connector_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Unknown connector")
    return c


@router.post("/{connector_id:path}/approval")
def set_approval(connector_id: str, body: ApprovalBody, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    c = _get(connector_id, db)
    c.approval, c.approved_by, c.approval_note = body.approval, admin.id, body.note
    db.commit()
    return payload(c)


@router.post("/{connector_id:path}/probe")
def probe_connector(connector_id: str, body: ProbeBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    c = _get(connector_id, db)
    if c.transport != "remote" or not c.remote_url:
        return {"ok": False, "error": f"This connector runs locally ({c.transport}); install it in your client with the snippet shown.", "tools": [], "tool_count": 0, "auth_required": False, "latency_ms": 0, "server": {}, "protocol": ""}
    return probe(c.remote_url, body.headers, loopback_user=user)


@router.post("/{connector_id:path}/call")
def call_connector(connector_id: str, body: CallBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    c = _get(connector_id, db)
    if c.approval != "approved" and user.role != "admin":
        raise HTTPException(status_code=403, detail="Connector is not approved")
    if c.transport != "remote":
        raise HTTPException(status_code=400, detail="Only remote connectors can be called from the playground")
    client = McpClient(c.remote_url, body.headers, loopback_user=user)
    try:
        client.initialize()
        result = client.call_tool(body.tool, body.arguments)
    except McpError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"tool": body.tool, "text": tool_result_text(result), "is_error": bool(result.get("isError")), "raw": result}


@router.get("/{connector_id:path}")
def get_connector(connector_id: str, _: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    return payload(_get(connector_id, db))
