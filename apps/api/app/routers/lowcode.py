from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_db
from app.lowcode import (
    LANDSCAPE,
    STUDIOS,
    category_blurb,
    category_for,
    copilot_recipe,
    langflow_flow,
    n8n_workflow,
    playground_mcp_url,
    recommend_connectors,
)
from app.models import User
from app.routers.faces import _manifest

router = APIRouter(prefix="/v1/lowcode", tags=["lowcode"])


def _entry_like(manifest: dict) -> dict:
    """The category rule reads catalog-entry fields; a manifest carries them under slightly different names."""
    return {**manifest, "family": manifest.get("family", "Domain"), "connectors": manifest.get("connectors") or []}


@router.get("/landscape")
def landscape(_: User = Depends(current_user)) -> dict:
    return {"platforms": LANDSCAPE, "studios": STUDIOS, "playground_mcp_url": playground_mcp_url()}


@router.get("/{blueprint_id}")
def tracks(blueprint_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Both tracks for one blueprint: what the low-code studios get, and where the code track lives."""
    m = _manifest(blueprint_id)
    category = category_for(_entry_like(m))
    return {
        "blueprint_id": m["id"], "name": m["name"], "category": category, "category_blurb": category_blurb(category),
        "lowcode": [{**s, "artefact_url": f"/v1/lowcode/{m['id']}/{s['id']}", "download_url": f"/v1/lowcode/{m['id']}/{s['id']}?download=1"} for s in STUDIOS],
        "code": [
            {"id": "notebook", "name": "Notebook", "blurb": "Runs end to end on mock data in the browser or the sandbox", "href": f"/build/notebooks?blueprint={m['id']}"},
            {"id": "frameworks", "name": "Frameworks", "blurb": "OpenAI Agents SDK, LangGraph, CrewAI, Agent Framework, ADK projects", "href": f"/discover/frameworks?blueprint={m['id']}"},
            {"id": "deploy", "name": "Deploy", "blurb": "Azure AI Foundry, Anthropic Managed Agents, AWS AgentCore, Google Agent Engine", "href": f"/discover/clouds?blueprint={m['id']}"},
            {"id": "evals", "name": "Evaluate", "blurb": "Golden cases, gates and a nightly canary", "href": f"/evaluate/evals?blueprint={m['id']}"},
        ],
        "recommended_connectors": recommend_connectors(db, m),
    }


@router.get("/{blueprint_id}/{studio}")
def artefact(blueprint_id: str, studio: str, download: bool = Query(default=False), user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    m = _manifest(blueprint_id)
    category = category_for(_entry_like(m))
    slug = m["id"]
    if studio == "langflow":
        body, media, name = json.dumps(langflow_flow(m, category), indent=2), "application/json", f"{slug}-langflow.json"
    elif studio == "n8n":
        body, media, name = json.dumps(n8n_workflow(m, category), indent=2), "application/json", f"{slug}-n8n.json"
    elif studio == "copilot":
        recipe = copilot_recipe(m, category, recommend_connectors(db, m, k=3))
        if download:
            body, media, name = recipe["markdown"], "text/markdown; charset=utf-8", f"{slug}-copilot-studio.md"
        else:
            body, media, name = json.dumps(recipe), "application/json", f"{slug}-copilot-studio.json"
    else:
        raise HTTPException(status_code=404, detail="Unknown studio")
    headers = {"Content-Disposition": f'attachment; filename="{name}"'} if download else {}
    return Response(body, media_type=media, headers=headers)
