"""Notebook, framework, cloud and custom-agent endpoints: the four faces of a blueprint."""

from __future__ import annotations

import json
import re
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.core import REGISTRY
from app.auth import current_user
from app.catalog import get_model
from app.catalog_store import get_entry, manifest_for
from app.config import settings
from app.db import get_db
from app.deploy import CLOUDS, render_script
from app.evals import current_agent_version, rollback_agent, snapshot_agent
from app.flavors import FRAMEWORKS, render_project, zip_project
from app.governance import allowed_model_ids, check_budget, check_policy, policy_for
from app.keys import available_providers, resolve_key
from app.llm import ProviderError, complete
from app.models import AgentVersion, Conversation, CustomAgent, Run, UsageEvent, User
from app.notebooks import (
    HELPER,
    compute_options,
    execute,
    execute_notebook,
    gallery,
    notebook_blank,
    notebook_for_blueprint,
    notebook_for_conversation,
    notebook_for_gallery,
    notebook_for_run,
    pip_install,
)
from app.router import SMART, route
from app.routers.runs import _payload as run_payload
from app.skills import skill_prompt

router = APIRouter(tags=["faces"])
IPYNB = "application/x-ipynb+json"


def _manifest(blueprint_id: str) -> dict:
    bp = REGISTRY.get(blueprint_id)
    if bp is not None and bp.family != "Runtime":
        return bp.manifest()
    entry = get_entry(blueprint_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Unknown blueprint")
    return manifest_for(entry)


# ---------- notebooks ----------

@router.get("/v1/notebooks/playground.py")
def nb_helper(_: User = Depends(current_user)) -> Response:
    """The helper module notebooks import; the browser runtime fetches it under the person's session."""
    return Response(HELPER, media_type="text/x-python")


@router.get("/v1/notebooks/gallery")
def nb_gallery(_: User = Depends(current_user)) -> dict:
    manifests = [bp.manifest() for bp in REGISTRY.values() if bp.family not in ("Runtime", "Platform")]
    return {"notebooks": gallery(manifests)}


@router.get("/v1/notebooks/gallery/{slug}.ipynb")
def nb_gallery_item(slug: str, _: User = Depends(current_user)) -> Response:
    nb = notebook_for_gallery(slug)
    if nb is None:
        raise HTTPException(status_code=404, detail="Unknown notebook")
    return Response(json.dumps(nb), media_type=IPYNB)


@router.get("/v1/notebooks/compute")
def nb_compute(path: str = Query(min_length=1, max_length=300), _: User = Depends(current_user)) -> dict:
    """Where this notebook can run, with deep links for external compute."""
    if not path.startswith("/v1/notebooks/") or not path.endswith(".ipynb"):
        raise HTTPException(status_code=400, detail="Not a notebook path")
    return {"options": compute_options(path, path.rsplit("/", 1)[-1])}


class NotebookExecuteBody(BaseModel):
    path: str | None = Field(default=None, max_length=300)
    cells: list[str] | None = Field(default=None, max_length=60)
    timeout: int = Field(default=300, ge=10, le=600)


def _sandbox_env(user: User) -> dict[str, str]:
    return {
        "PLAYGROUND_API_URL": settings.self_url, "PLAYGROUND_INTERNAL_KEY": settings.internal_key, "PLAYGROUND_USER_ID": user.id,
        "PLAYGROUND_USER_EMAIL": user.email, "PLAYGROUND_USER_NAME": user.name, "PLAYGROUND_USER_ROLE": user.role, "PLAYGROUND_USER_DEPARTMENT": user.department,
    }


def _notebook_by_path(path: str, user: User, db: Session) -> dict:
    """Resolve a generated notebook by its API path so the sandbox runs exactly what the browser shows."""
    if path == "/v1/notebooks/blank.ipynb":
        return notebook_blank()
    m = re.match(r"^/v1/notebooks/(gallery|blueprint|run|conversation)/([A-Za-z0-9_.-]+)\.ipynb$", path)
    if m is None:
        raise HTTPException(status_code=400, detail="Not a notebook path")
    kind, key = m.groups()
    if kind == "gallery":
        nb = notebook_for_gallery(key)
        if nb is None:
            raise HTTPException(status_code=404, detail="Unknown notebook")
        return nb
    if kind == "blueprint":
        return notebook_for_blueprint(_manifest(key))
    if kind == "run":
        run = db.get(Run, key)
        if run is None or (run.user_id != user.id and user.role not in ("admin", "champion")):
            raise HTTPException(status_code=404, detail="Run not found")
        return notebook_for_run(run_payload(run), _manifest(run.blueprint_id))
    c = db.get(Conversation, key)
    if c is None or c.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return notebook_for_conversation({"title": c.title, "model": c.model, "messages": [{"role": mm.role, "content": mm.content} for mm in c.messages]})


@router.post("/v1/notebooks/execute")
def nb_execute(body: NotebookExecuteBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Run a whole notebook (by path, or explicit cells) in the sandbox and return each cell's output."""
    if body.cells is None and not body.path:
        raise HTTPException(status_code=400, detail="Give a notebook path or cells")
    cells = body.cells if body.cells is not None else [c["source"] if isinstance(c["source"], str) else "".join(c["source"]) for c in _notebook_by_path(body.path or "", user, db)["cells"] if c["cell_type"] == "code"]
    result = execute_notebook(cells, _sandbox_env(user), user.id, timeout=body.timeout)
    db.add(UsageEvent(user_id=user.id, feature="notebook", model="sandbox", provider=result["backend"], latency_ms=result["ms"], status="ok" if result["ok"] else "error"))
    db.commit()
    return result


class PipBody(BaseModel):
    packages: list[str] = Field(min_length=1, max_length=20)


@router.post("/v1/sandbox/pip")
def sandbox_pip(body: PipBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Install packages into the caller's sandbox environment; they stay for later runs."""
    if settings.sandbox_endpoint:
        return {"ok": False, "stdout": "", "stderr": "Use %pip install inside a cell: dynamic sessions install packages per session.", "ms": 0}
    result = pip_install(user.id, [p.strip() for p in body.packages])
    db.add(UsageEvent(user_id=user.id, feature="notebook", model="pip", provider="local", latency_ms=result["ms"], status="ok" if result["ok"] else "error"))
    db.commit()
    return result


class HeartbeatBody(BaseModel):
    path: str = Field(max_length=300)
    mode: str = Field(default="browser", pattern="^(browser|sandbox)$")


@router.post("/v1/notebooks/heartbeat", status_code=202)
def nb_heartbeat(body: HeartbeatBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Editor activity for the adoption clock: one zero-cost ledger row every few minutes while a notebook is open."""
    db.add(UsageEvent(user_id=user.id, feature="notebook", model=f"editor-{body.mode}", provider="playground", status="ok"))
    db.commit()
    return {"recorded": True}


@router.get("/v1/notebooks/blank.ipynb")
def nb_blank(_: User = Depends(current_user)) -> Response:
    return Response(json.dumps(notebook_blank()), media_type=IPYNB)


@router.get("/v1/notebooks/blueprint/{blueprint_id}.ipynb")
def nb_blueprint(blueprint_id: str, _: User = Depends(current_user)) -> Response:
    return Response(json.dumps(notebook_for_blueprint(_manifest(blueprint_id))), media_type=IPYNB)


@router.get("/v1/notebooks/run/{run_id}.ipynb")
def nb_run(run_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    run = db.get(Run, run_id)
    if run is None or (run.user_id != user.id and user.role not in ("admin", "champion")):
        raise HTTPException(status_code=404, detail="Run not found")
    return Response(json.dumps(notebook_for_run(run_payload(run), _manifest(run.blueprint_id))), media_type=IPYNB)


@router.get("/v1/notebooks/conversation/{conversation_id}.ipynb")
def nb_conversation(conversation_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    c = db.get(Conversation, conversation_id)
    if c is None or c.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv = {"title": c.title, "model": c.model, "messages": [{"role": m.role, "content": m.content} for m in c.messages]}
    return Response(json.dumps(notebook_for_conversation(conv)), media_type=IPYNB)


class SandboxBody(BaseModel):
    code: str = Field(min_length=1, max_length=20000)
    session_id: str | None = None


@router.post("/v1/sandbox/execute")
def sandbox_execute(body: SandboxBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    result = execute(body.code, _sandbox_env(user), body.session_id or f"{user.id}-{uuid.uuid4().hex[:8]}", user_id=user.id)
    db.add(UsageEvent(user_id=user.id, feature="notebook", model="sandbox", provider=result["backend"], latency_ms=result["ms"], status="ok" if result["exit_code"] == 0 else "error"))
    db.commit()
    return result


class CompleteBody(BaseModel):
    model: str
    messages: list[dict]
    max_tokens: int = Field(default=1024, ge=1, le=16000)


@router.post("/v1/chat/complete")
def chat_complete(body: CompleteBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Non-streaming completion for notebooks and scripts, governed exactly like the playground."""
    model_id = body.model
    routed = False
    if model_id == SMART:
        prompt = next((m.get("content", "") for m in reversed(body.messages) if m.get("role") == "user"), "")
        decision = route(prompt, allowed_model_ids(db, user.role), providers=set(available_providers(db, user, "notebook")))
        if decision is None:
            raise HTTPException(status_code=400, detail="No model with a usable key is available for your role. Add a provider key from the Keys drawer.")
        model_id, routed = decision.model, True
    spec = get_model(model_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Unknown model")
    denial = check_policy(db, user, spec)
    if denial:
        raise HTTPException(status_code=403, detail=denial)
    budget = check_budget(db, user)
    if not budget.allowed:
        raise HTTPException(status_code=402, detail=budget.reason)
    api_key, key_source, key_extra = resolve_key(db, user.id, spec.provider, "notebook")
    if key_source == "none":
        raise HTTPException(status_code=402, detail=f"No {spec.provider} key is available. Add your own {spec.provider} key from the Keys drawer, or ask an admin to enable the platform key.")
    max_tokens = min(body.max_tokens, policy_for(db, user.role).max_tokens)
    started = time.perf_counter()
    try:
        text, usage = complete(model_id, body.messages, max_tokens=max_tokens, api_key=api_key, api_base=key_extra.get("api_base"))
    except ProviderError as exc:
        db.add(UsageEvent(user_id=user.id, feature="notebook", model=model_id, provider=spec.provider, status="error", latency_ms=int((time.perf_counter() - started) * 1000)))
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    db.add(UsageEvent(user_id=user.id, feature="notebook", model=model_id, provider=spec.provider, tokens_in=usage.tokens_in, tokens_out=usage.tokens_out, tokens_cached=usage.tokens_cached, cost_usd=usage.cost_usd, latency_ms=usage.latency_ms, status="ok", routed=routed, key_source=key_source))
    db.commit()
    return {"text": text, "model": model_id, "routed": routed, "key_source": key_source, "tokens_in": usage.tokens_in, "tokens_out": usage.tokens_out, "cost_usd": usage.cost_usd, "latency_ms": usage.latency_ms}


# ---------- frameworks ----------

@router.get("/v1/frameworks")
def frameworks(_: User = Depends(current_user)) -> dict:
    return {"frameworks": [{"id": k, **v} for k, v in FRAMEWORKS.items()]}


@router.get("/v1/blueprints/{blueprint_id}/flavor/{framework}")
def flavor(blueprint_id: str, framework: str, _: User = Depends(current_user)) -> dict:
    if framework not in FRAMEWORKS:
        raise HTTPException(status_code=404, detail="Unknown framework")
    files = render_project(_manifest(blueprint_id), framework)
    return {"blueprint_id": blueprint_id, "framework": framework, "files": files, "download": f"/v1/blueprints/{blueprint_id}/flavor/{framework}/download"}


@router.get("/v1/blueprints/{blueprint_id}/flavor/{framework}/download")
def flavor_zip(blueprint_id: str, framework: str, _: User = Depends(current_user)) -> Response:
    if framework not in FRAMEWORKS:
        raise HTTPException(status_code=404, detail="Unknown framework")
    data = zip_project(render_project(_manifest(blueprint_id), framework), f"{blueprint_id}-{framework}")
    return Response(data, media_type="application/zip", headers={"content-disposition": f'attachment; filename="{blueprint_id}-{framework}.zip"'})


# ---------- clouds ----------

@router.get("/v1/clouds")
def clouds(_: User = Depends(current_user)) -> dict:
    return {"clouds": [{"id": k, **v} for k, v in CLOUDS.items()]}


@router.get("/v1/blueprints/{blueprint_id}/deploy/{cloud}")
def deploy(blueprint_id: str, cloud: str, _: User = Depends(current_user)) -> dict:
    if cloud not in CLOUDS:
        raise HTTPException(status_code=404, detail="Unknown cloud")
    return render_script(_manifest(blueprint_id), cloud)


# ---------- custom agents (no-code wizard) ----------

class CustomAgentBody(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=5, max_length=400)
    instructions: str = Field(min_length=20, max_length=8000)
    knowledge: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)  # approved connector ids
    skills: list[str] = Field(default_factory=list)
    starters: list[str] = Field(default_factory=list)
    published: bool = False


def _custom_payload(a: CustomAgent) -> dict:
    return {"id": a.id, "name": a.name, "description": a.description, "instructions": a.instructions, "knowledge": a.knowledge or [], "tools": a.tools or [], "skills": a.skills or [], "starters": a.starters or [], "published": a.published, "owner_id": a.user_id, "created_at": a.created_at.isoformat()}


@router.get("/v1/custom-agents")
def list_custom(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(CustomAgent).where((CustomAgent.user_id == user.id) | (CustomAgent.published.is_(True))).order_by(CustomAgent.created_at.desc())).all()
    return {"agents": [_custom_payload(a) for a in rows]}


@router.post("/v1/custom-agents", status_code=201)
def create_custom(body: CustomAgentBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    a = CustomAgent(id=f"custom-{uuid.uuid4().hex[:12]}", user_id=user.id, **body.model_dump())
    db.add(a)
    db.commit()
    return _custom_payload(a)


class CustomAgentPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, min_length=5, max_length=400)
    instructions: str | None = Field(default=None, min_length=20, max_length=8000)
    knowledge: list[str] | None = None
    tools: list[str] | None = None
    skills: list[str] | None = None
    starters: list[str] | None = None
    published: bool | None = None
    note: str = Field(default="", max_length=400)


class RollbackBody(BaseModel):
    version: int = Field(ge=1)


def _owned_agent(agent_id: str, user: User, db: Session) -> CustomAgent:
    a = db.get(CustomAgent, agent_id)
    if a is None or (a.user_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="Agent not found")
    return a


@router.patch("/v1/custom-agents/{agent_id}")
def patch_custom(agent_id: str, body: CustomAgentPatch, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Every edit keeps the previous state as a numbered version, so a canary can roll back to the last good one."""
    a = _owned_agent(agent_id, user, db)
    changes = body.model_dump(exclude_none=True)
    note = changes.pop("note", "")
    if not changes:
        return _custom_payload(a)
    db.add(AgentVersion(agent_id=a.id, version=current_agent_version(db, a.id) or 1, snapshot=snapshot_agent(a), note=note or "Edited in the wizard"))
    for k, v in changes.items():
        setattr(a, k, v)
    db.commit()
    return {**_custom_payload(a), "version": current_agent_version(db, a.id)}


@router.get("/v1/custom-agents/{agent_id}/versions")
def agent_versions(agent_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    a = _owned_agent(agent_id, user, db)
    rows = db.scalars(select(AgentVersion).where(AgentVersion.agent_id == a.id).order_by(AgentVersion.version)).all()
    return {"current": current_agent_version(db, a.id), "versions": [{"version": v.version, "note": v.note, "created_at": v.created_at.isoformat(), "snapshot": v.snapshot} for v in rows]}


@router.post("/v1/custom-agents/{agent_id}/rollback")
def agent_rollback(agent_id: str, body: RollbackBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    a = _owned_agent(agent_id, user, db)
    if not rollback_agent(db, a, body.version, f"Manual rollback by {user.name}"):
        raise HTTPException(status_code=404, detail="Version not found")
    return {**_custom_payload(a), "version": current_agent_version(db, a.id)}


@router.delete("/v1/custom-agents/{agent_id}", status_code=204)
def delete_custom(agent_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    a = db.get(CustomAgent, agent_id)
    if a is None or a.user_id != user.id:
        raise HTTPException(status_code=404, detail="Agent not found")
    db.delete(a)
    db.commit()


@router.get("/v1/custom-agents/{agent_id}/export/declarative-agent")
def export_declarative(agent_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    """Microsoft 365 declarative agent manifest, the format Copilot Studio and the Agent Builder import."""
    a = db.get(CustomAgent, agent_id)
    if a is None or (a.user_id != user.id and not a.published):
        raise HTTPException(status_code=404, detail="Agent not found")
    manifest = {
        "$schema": "https://developer.microsoft.com/json-schemas/copilot/declarative-agent/v1.5/schema.json",
        "version": "v1.5",
        "name": a.name[:100],
        "description": a.description[:1000],
        "instructions": (a.instructions + ("\n\n" + skill_prompt(a.skills or [], max_chars=3000) if a.skills else ""))[:8000],
        "conversation_starters": [{"title": s[:50], "text": s[:200]} for s in (a.starters or [])[:6]],
        "capabilities": ([{"name": "OneDriveAndSharePoint", "items_by_url": []}] if a.knowledge else []),
    }
    return Response(json.dumps(manifest, indent=2), media_type="application/json", headers={"content-disposition": f'attachment; filename="{a.id}-declarativeAgent.json"'})
