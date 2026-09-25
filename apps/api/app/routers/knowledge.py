from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_db
from app.knowledge import (
    EMBEDDING_MODELS,
    can_edit,
    can_see,
    dataset_units,
    decode_upload,
    delete_document,
    delete_space,
    document_payload,
    embedding_available,
    extract_text,
    fetch_url,
    ingest_text,
    search,
    space_payload,
    visible_spaces,
)
from app.models import KnowledgeDocument, KnowledgeSpace, Run, User
from app.repo_map import map_repository

router = APIRouter(prefix="/v1/knowledge", tags=["knowledge"])


class SpaceBody(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=400)
    visibility: str = Field(default="private", pattern="^(private|department|org)$")
    embedding_model: str = Field(default="local-hash")


class TextBody(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=2_000_000)


class UrlBody(BaseModel):
    url: str = Field(min_length=8, max_length=512)


class FileBody(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_base64: str = Field(min_length=1, max_length=12_000_000)


class DatasetBody(BaseModel):
    dataset: str


class RepoBody(BaseModel):
    source: str = Field(min_length=1, max_length=512)  # GitHub URL or a local path under an allowed root


class SearchBody(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    k: int = Field(default=5, ge=1, le=20)


class AskBody(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


@router.get("/embedding-models")
def embedding_models(_: User = Depends(current_user)) -> dict:
    return {"models": [{"id": k, **v, "available": embedding_available(k)} for k, v in EMBEDDING_MODELS.items()]}


@router.get("/spaces")
def list_spaces(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    spaces = visible_spaces(db, user)
    owners = {u.id: u for u in db.scalars(select(User).where(User.id.in_({s.owner_id for s in spaces}))).all()} if spaces else {}
    return {"spaces": [space_payload(s, owners.get(s.owner_id)) for s in spaces]}


@router.post("/spaces", status_code=201)
def create_space(body: SpaceBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    if body.embedding_model not in EMBEDDING_MODELS:
        raise HTTPException(status_code=400, detail="Unknown embedding model")
    s = KnowledgeSpace(owner_id=user.id, name=body.name, description=body.description, visibility=body.visibility, department=user.department, embedding_model=body.embedding_model)
    db.add(s)
    db.commit()
    return space_payload(s, user)


def _space(space_id: str, user: User, db: Session, edit: bool = False) -> KnowledgeSpace:
    s = db.get(KnowledgeSpace, space_id)
    if s is None or not can_see(s, user):
        raise HTTPException(status_code=404, detail="Knowledge Space not found")
    if edit and not can_edit(s, user):
        raise HTTPException(status_code=403, detail="Only the owner or an admin can change this space")
    return s


@router.get("/spaces/{space_id}")
def get_space(space_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    s = _space(space_id, user, db)
    docs = db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.space_id == s.id).order_by(KnowledgeDocument.created_at.desc())).all()
    owner = db.get(User, s.owner_id)
    return {**space_payload(s, owner), "documents": [document_payload(d) for d in docs], "can_edit": can_edit(s, user)}


@router.delete("/spaces/{space_id}", status_code=204)
def remove_space(space_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    delete_space(db, _space(space_id, user, db, edit=True))


@router.post("/spaces/{space_id}/documents/text", status_code=201)
def add_text(space_id: str, body: TextBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    s = _space(space_id, user, db, edit=True)
    return document_payload(ingest_text(db, s, user, body.title, body.text, "text"))


@router.post("/spaces/{space_id}/documents/url", status_code=201)
def add_url(space_id: str, body: UrlBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    s = _space(space_id, user, db, edit=True)
    try:
        title, text = fetch_url(body.url)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not fetch the page: {str(exc)[:200]}") from exc
    if not text.strip():
        raise HTTPException(status_code=400, detail="The page had no readable text")
    return document_payload(ingest_text(db, s, user, title, text, "url", body.url))


@router.post("/spaces/{space_id}/documents/file", status_code=201)
def add_file(space_id: str, body: FileBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    s = _space(space_id, user, db, edit=True)
    try:
        text = extract_text(body.filename, decode_upload(body.content_base64))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read {body.filename}: {str(exc)[:200]}") from exc
    if not text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from the file")
    return document_payload(ingest_text(db, s, user, body.filename, text, "file", body.filename))


@router.post("/spaces/{space_id}/documents/dataset", status_code=201)
def add_dataset(space_id: str, body: DatasetBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    s = _space(space_id, user, db, edit=True)
    try:
        title, chunks, metas = dataset_units(body.dataset)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return document_payload(ingest_text(db, s, user, title, "\n\n".join(chunks), "dataset", body.dataset, metas=metas, chunks=chunks))


@router.post("/spaces/{space_id}/documents/repo", status_code=201)
def add_repo(space_id: str, body: RepoBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    s = _space(space_id, user, db, edit=True)
    try:
        result = map_repository(body.source)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Path not found: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not map the repository: {str(exc)[:200]}") from exc
    chunks = [c for c, _ in result["chunks"]]
    metas = [m for _, m in result["chunks"]]
    graph = {"nodes": result["nodes"], "edges": result["edges"], "summary": result["summary"]}
    title = body.source.rstrip("/").split("/")[-1] or body.source
    doc = ingest_text(db, s, user, f"Repository: {title}", "\n\n".join(chunks), "repo", body.source, metas=metas, chunks=chunks, graph=graph)
    return {**document_payload(doc), "summary": result["summary"]}


@router.delete("/spaces/{space_id}/documents/{doc_id}", status_code=204)
def remove_document(space_id: str, doc_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    s = _space(space_id, user, db, edit=True)
    d = db.get(KnowledgeDocument, doc_id)
    if d is None or d.space_id != s.id:
        raise HTTPException(status_code=404, detail="Document not found")
    delete_document(db, s, d)


@router.get("/spaces/{space_id}/graph")
def space_graph(space_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    s = _space(space_id, user, db)
    docs = db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.space_id == s.id, KnowledgeDocument.graph.is_not(None))).all()
    nodes, edges, summaries = [], [], []
    for d in docs:
        g = d.graph or {}
        nodes.extend({**n, "doc_id": d.id} for n in g.get("nodes", []))
        edges.extend(g.get("edges", []))
        summaries.append({"doc_id": d.id, "title": d.title, **g.get("summary", {})})
    return {"nodes": nodes, "edges": edges, "documents": summaries}


@router.post("/spaces/{space_id}/search")
def search_space(space_id: str, body: SearchBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    s = _space(space_id, user, db)
    return {"hits": search(db, s, body.query, k=body.k), "embedding_model": s.embedding_model}


@router.post("/spaces/{space_id}/ask")
def ask_space(space_id: str, body: AskBody, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    """Grounded answer through the Knowledge Q&A blueprint, so it is checkpointed, metered and reviewable like any run."""
    from app.agents.runtime import start_run
    from app.governance import check_budget
    from app.routers.runs import _payload

    s = _space(space_id, user, db)
    budget = check_budget(db, user)
    if not budget.allowed:
        raise HTTPException(status_code=402, detail=budget.reason)
    run = Run(blueprint_id="knowledge-qa", user_id=user.id, input={"question": body.question, "space_id": s.id}, status="queued")
    db.add(run)
    db.commit()
    start_run(run, background=False)
    db.expire_all()
    return _payload(db.get(Run, run.id))
