from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth import current_user
from app.db import get_db
from app.models import Conversation, Message, User
from app.schemas import ConversationCreate, ConversationPatch

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


def _summary(c: Conversation, db: Session) -> dict:
    count = db.scalar(select(Message.id).where(Message.conversation_id == c.id).limit(1))
    return {
        "id": c.id, "title": c.title, "model": c.model, "tags": c.tags or [], "pinned": c.pinned,
        "system_prompt": c.system_prompt, "created_at": c.created_at.isoformat(), "updated_at": c.updated_at.isoformat(),
        "has_messages": bool(count),
    }


@router.get("")
def list_conversations(
    q: str = Query(default=""), tag: str = Query(default=""), limit: int = Query(default=50, le=200),
    user: User = Depends(current_user), db: Session = Depends(get_db),
) -> dict:
    stmt = select(Conversation).where(Conversation.user_id == user.id)
    if q:
        like = f"%{q}%"
        matched_ids = select(Message.conversation_id).where(Message.content.ilike(like))
        stmt = stmt.where(or_(Conversation.title.ilike(like), Conversation.id.in_(matched_ids)))
    stmt = stmt.order_by(Conversation.pinned.desc(), Conversation.updated_at.desc()).limit(limit)
    items = [_summary(c, db) for c in db.scalars(stmt)]
    if tag:
        items = [i for i in items if tag in i["tags"]]
    return {"conversations": items}


@router.post("", status_code=201)
def create_conversation(body: ConversationCreate, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    c = Conversation(user_id=user.id, title=body.title, model=body.model, system_prompt=body.system_prompt, tags=body.tags)
    db.add(c)
    db.commit()
    return _summary(c, db)


def _owned(conversation_id: str, user: User, db: Session) -> Conversation:
    c = db.get(Conversation, conversation_id)
    if c is None or c.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return c


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    c = _owned(conversation_id, user, db)
    return {
        **_summary(c, db),
        "messages": [
            {
                "id": m.id, "role": m.role, "content": m.content, "model": m.model, "tokens_in": m.tokens_in,
                "tokens_out": m.tokens_out, "cost_usd": m.cost_usd, "latency_ms": m.latency_ms, "created_at": m.created_at.isoformat(),
            }
            for m in c.messages
        ],
    }


@router.patch("/{conversation_id}")
def patch_conversation(conversation_id: str, body: ConversationPatch, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    c = _owned(conversation_id, user, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    db.commit()
    return _summary(c, db)


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> None:
    c = _owned(conversation_id, user, db)
    db.delete(c)
    db.commit()
