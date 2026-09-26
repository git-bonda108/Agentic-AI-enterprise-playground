"""Runs blueprints on LangGraph with a persisted checkpointer, in worker threads, with the run row as the viewer's source of truth."""

from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import UTC, datetime
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from app.agents.core import REGISTRY, RunContext
from app.config import API_DIR, settings
from app.db import SessionLocal
from app.governance import allowed_model_ids
from app.models import Run, User

logger = logging.getLogger("playground.runtime")

CONTEXTS: dict[str, RunContext] = {}
_graphs: dict[str, Any] = {}
_checkpointer: SqliteSaver | None = None
_lock = threading.RLock()  # re-entrant: graph_for() calls get_checkpointer() while holding it


def checkpoint_path() -> str:
    override = getattr(settings, "checkpoint_path", "")
    return override or str(API_DIR / "checkpoints.db")


def get_checkpointer() -> SqliteSaver:
    global _checkpointer
    with _lock:
        if _checkpointer is None:
            conn = sqlite3.connect(checkpoint_path(), check_same_thread=False)
            _checkpointer = SqliteSaver(conn)
        return _checkpointer


def reset_runtime() -> None:
    """Drop the in-memory graph cache and checkpointer connection (tests simulate an API restart with this)."""
    global _checkpointer
    with _lock:
        _graphs.clear()
        CONTEXTS.clear()
        if _checkpointer is not None:
            _checkpointer.conn.close()
        _checkpointer = None


def graph_for(blueprint_id: str):
    """Executable blueprints build their own graph; catalog entries share the generic prompt-agent graph."""
    key = blueprint_id if blueprint_id in REGISTRY else "prompt-agent"
    with _lock:
        if key not in _graphs:
            bp = REGISTRY[key]
            _graphs[key] = bp.build(get_checkpointer())
        return _graphs[key]


def context_for(run: Run) -> RunContext:
    ctx = CONTEXTS.get(run.id)
    if ctx is None:
        from app.keys import available_providers

        feature = "canary" if run.source == "canary" else "agent"
        with SessionLocal() as db:
            user = db.get(User, run.user_id)
            allowed = allowed_model_ids(db, user.role) if user else None
            providers = available_providers(db, user, feature)
        ctx = RunContext(run_id=run.id, blueprint_id=run.blueprint_id, user_id=run.user_id, allowed_models=allowed, providers=providers, feature=feature)
        CONTEXTS[run.id] = ctx
    return ctx


def _update(run_id: str, **fields: Any) -> None:
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        if run is None:
            return
        for k, v in fields.items():
            setattr(run, k, v)
        run.updated_at = datetime.now(UTC)
        db.commit()


def _consume(run_id: str, blueprint_id: str, stream) -> None:
    """Drain a graph stream, mirroring steps, interrupts and the final output onto the run row."""
    steps: list[dict] = []
    output = None
    interrupted: dict | None = None
    for event in stream:
        if "__interrupt__" in event:
            payload = event["__interrupt__"][0].value if event["__interrupt__"] else {}
            interrupted = payload if isinstance(payload, dict) else {"question": str(payload)}
            continue
        for update in event.values():
            if not isinstance(update, dict):
                continue
            if "steps" in update:
                steps = update["steps"]
                _update(run_id, steps=steps)
            if update.get("output") is not None:
                output = update["output"]
    if interrupted is not None:
        _update(run_id, status="waiting_review", review=interrupted, steps=steps)
        return
    _update(run_id, status="completed", output=output, steps=steps, finished_at=datetime.now(UTC))


def _execute(run_id: str, blueprint_id: str, payload: Any) -> None:
    graph = graph_for(blueprint_id)
    config = {"configurable": {"thread_id": run_id, "run_id": run_id}}
    try:
        _update(run_id, status="running", review=None, error=None)
        _consume(run_id, blueprint_id, graph.stream(payload, config, stream_mode="updates"))
    except Exception as exc:  # any failure is recorded on the run, never lost in a thread
        logger.exception("run %s failed", run_id)
        _update(run_id, status="failed", error=str(exc)[:1000], finished_at=datetime.now(UTC))


def start_run(run: Run, *, background: bool = True) -> None:
    context_for(run)
    payload = {"input": run.input, "data": {}, "steps": [], "output": None, "review": None, "error": None}
    if background:
        threading.Thread(target=_execute, args=(run.id, run.blueprint_id, payload), daemon=True).start()
    else:
        _execute(run.id, run.blueprint_id, payload)


def resume_run(run: Run, answer: Any, *, background: bool = True) -> None:
    context_for(run)
    if background:
        threading.Thread(target=_execute, args=(run.id, run.blueprint_id, Command(resume=answer)), daemon=True).start()
    else:
        _execute(run.id, run.blueprint_id, Command(resume=answer))


def ctx_from_config(config: dict) -> RunContext:
    """Nodes call this to get their metering context from the LangGraph config."""
    run_id = config["configurable"]["run_id"]
    ctx = CONTEXTS.get(run_id)
    if ctx is None:
        with SessionLocal() as db:
            run = db.get(Run, run_id)
        if run is None:
            raise RuntimeError(f"Unknown run {run_id}")
        ctx = context_for(run)
    return ctx
