import json
import logging
import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from app.auth import current_user
from app.catalog import estimate_cost, get_model
from app.db import get_db
from app.governance import allowed_model_ids, check_budget, check_policy, policy_for
from app.llm import ProviderError, stream_completion
from app.models import Conversation, Message, UsageEvent, User
from app.router import SMART, route
from app.schemas import ChatStreamRequest

logger = logging.getLogger("playground.chat")

router = APIRouter(prefix="/v1/chat", tags=["chat"])


async def _blocked(db: Session, user: User, req: ChatStreamRequest, model: str, reason: str, provider: str = "unknown"):
    """Emit a single error event and record the blocked attempt in the ledger."""
    logger.info("blocked user=%s model=%s: %s", user.id, model, reason)
    db.add(UsageEvent(user_id=user.id, feature=req.feature, model=model, provider=provider, status="blocked"))
    db.commit()
    yield {"event": "error", "data": json.dumps({"message": reason, "code": "blocked"})}
    yield {"event": "done", "data": "{}"}


def _title_from(messages: list) -> str:
    first = next((m.content for m in messages if m.role == "user"), "New conversation")
    return (first.strip().splitlines()[0] or "New conversation")[:60]


@router.post("/stream")
async def chat_stream(req: ChatStreamRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    # 1. Resolve Smart routing to a concrete model the caller is allowed to use.
    routed = False
    routed_tier: str | None = None
    baseline_model: str | None = None
    route_reason: str | None = None
    if req.model == SMART:
        if not policy_for(db, user.role).smart_enabled:
            return EventSourceResponse(_blocked(db, user, req, "smart", "Smart routing is disabled for your role."))
        prompt = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
        decision = route(prompt, allowed_model_ids(db, user.role))
        if decision is None:
            return EventSourceResponse(_blocked(db, user, req, "smart", "No model is available for your role."))
        req.model = decision.model
        routed, routed_tier, baseline_model, route_reason = True, decision.tier, decision.baseline_model, decision.reason
    spec = get_model(req.model)
    provider = spec.provider if spec else "unknown"
    if spec is None:
        return EventSourceResponse(_blocked(db, user, req, req.model, f"Unknown model '{req.model}'."))

    # 2. Policy and budget gates.
    denial = check_policy(db, user, spec)
    if denial:
        return EventSourceResponse(_blocked(db, user, req, req.model, denial, provider))
    budget = check_budget(db, user)
    if not budget.allowed:
        return EventSourceResponse(_blocked(db, user, req, req.model, budget.reason or "Budget exceeded", provider))
    policy = policy_for(db, user.role)
    if req.params.max_tokens is None or req.params.max_tokens > policy.max_tokens:
        req.params.max_tokens = policy.max_tokens

    conversation: Conversation | None = None
    if req.persist:
        if req.conversation_id:
            conversation = db.get(Conversation, req.conversation_id)
            if conversation is not None and conversation.user_id != user.id:
                conversation = None
        if conversation is None:
            conversation = Conversation(user_id=user.id, title=_title_from(req.messages), model=req.model, system_prompt=req.params.system or "")
            db.add(conversation)
            db.commit()
        last_user = next((m for m in reversed(req.messages) if m.role == "user"), None)
        if last_user is not None:
            db.add(Message(conversation_id=conversation.id, role="user", content=last_user.content))
            db.commit()

    wire_messages = [m.model_dump() for m in req.messages]
    if req.params.system and not any(m["role"] == "system" for m in wire_messages):
        wire_messages.insert(0, {"role": "system", "content": req.params.system})

    async def events():
        text_parts: list[str] = []
        started = time.perf_counter()
        meta = {
            "conversation_id": conversation.id if conversation else None, "title": conversation.title if conversation else None,
            "model": req.model, "routed": routed, "routed_tier": routed_tier, "route_reason": route_reason,
            "budget_warnings": budget.warnings, "user_spend_usd": round(budget.user_spend, 6), "user_cap_usd": budget.user_cap,
        }
        yield {"event": "meta", "data": json.dumps(meta)}
        try:
            async for item in stream_completion(req.model, wire_messages, req.params.model_dump()):
                if item["type"] == "delta":
                    text_parts.append(item["text"])
                    yield {"event": "delta", "data": json.dumps({"text": item["text"]})}
                elif item["type"] == "usage":
                    u = item["usage"]
                    message_id = None
                    if conversation is not None:
                        msg = Message(
                            conversation_id=conversation.id, role="assistant", content="".join(text_parts), model=req.model,
                            tokens_in=u.tokens_in, tokens_out=u.tokens_out, cost_usd=u.cost_usd, latency_ms=u.latency_ms,
                        )
                        db.add(msg)
                        db.flush()
                        message_id = msg.id
                    savings = 0.0
                    if routed and baseline_model:
                        savings = max(estimate_cost(baseline_model, u.tokens_in, u.tokens_out, u.tokens_cached) - u.cost_usd, 0.0)
                    db.add(UsageEvent(
                        user_id=user.id, conversation_id=conversation.id if conversation else None, message_id=message_id,
                        feature=req.feature, model=req.model, provider=provider, tokens_in=u.tokens_in, tokens_out=u.tokens_out,
                        tokens_cached=u.tokens_cached, cost_usd=u.cost_usd, latency_ms=u.latency_ms, status="ok",
                        routed=routed, routed_tier=routed_tier, savings_usd=round(savings, 8),
                    ))
                    db.commit()
                    yield {"event": "usage", "data": json.dumps({
                        "tokens_in": u.tokens_in, "tokens_out": u.tokens_out, "tokens_cached": u.tokens_cached,
                        "cost_usd": u.cost_usd, "latency_ms": u.latency_ms, "model": req.model, "provider": provider,
                        "message_id": message_id, "conversation_id": conversation.id if conversation else None,
                        "routed": routed, "routed_tier": routed_tier, "savings_usd": round(savings, 8),
                    })}
        except ProviderError as exc:
            logger.warning("provider error user=%s model=%s: %s", user.id, req.model, exc)
            db.add(UsageEvent(
                user_id=user.id, conversation_id=conversation.id if conversation else None, feature=req.feature, model=req.model,
                provider=provider, latency_ms=int((time.perf_counter() - started) * 1000), status="error",
            ))
            db.commit()
            yield {"event": "error", "data": json.dumps({"message": str(exc)})}
        yield {"event": "done", "data": "{}"}

    return EventSourceResponse(events(), ping=15)
