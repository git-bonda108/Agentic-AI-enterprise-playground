import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def new_id() -> str:
    return uuid.uuid4().hex


def now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="explorer")
    department: Mapped[str] = mapped_column(String(128), default="General")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), default="New conversation")
    model: Mapped[str] = mapped_column(String(128))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(String(32), ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class UsageEvent(Base):
    """One row per model call. The ledger of record for every cost view."""

    __tablename__ = "usage_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    message_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    feature: Mapped[str] = mapped_column(String(32), index=True)  # chat | compare | agent | notebook
    model: Mapped[str] = mapped_column(String(128), index=True)
    provider: Mapped[str] = mapped_column(String(64), index=True)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    tokens_cached: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="ok")  # ok | error | blocked
    routed: Mapped[bool] = mapped_column(Boolean, default=False)
    routed_tier: Mapped[str | None] = mapped_column(String(16), nullable=True)
    savings_usd: Mapped[float] = mapped_column(Float, default=0.0)
    run_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    blueprint_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class Run(Base):
    """One execution of a blueprint. Steps and output are denormalized here for the run viewer; the graph state lives in the checkpointer."""

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    blueprint_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)  # queued | running | waiting_review | completed | failed
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    steps: Mapped[list[dict]] = mapped_column(JSON, default=list)
    review: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Policy(Base):
    """What a role may use. Empty provider list means every provider."""

    __tablename__ = "policies"

    role: Mapped[str] = mapped_column(String(32), primary_key=True)
    allowed_tiers: Mapped[list[str]] = mapped_column(JSON, default=list)
    allowed_providers: Mapped[list[str]] = mapped_column(JSON, default=list)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    smart_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Budget(Base):
    """Monthly USD cap for the org, a department, or one user. Key is 'org', the department name, or the user id."""

    __tablename__ = "budgets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    scope: Mapped[str] = mapped_column(String(16), index=True)  # org | department | user | user_default
    key: Mapped[str] = mapped_column(String(128), index=True)
    monthly_cap_usd: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class CustomAgent(Base):
    """An agent built in the no-code wizard: instructions, knowledge, starters. Runs on the generic prompt-agent graph."""

    __tablename__ = "custom_agents"

    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(400))
    instructions: Mapped[str] = mapped_column(Text)
    knowledge: Mapped[list[str]] = mapped_column(JSON, default=list)
    tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    starters: Mapped[list[str]] = mapped_column(JSON, default=list)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Alert(Base):
    """Raised once per period when a budget crosses 50, 80 or 100 percent."""

    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    scope: Mapped[str] = mapped_column(String(16))
    key: Mapped[str] = mapped_column(String(128))
    label: Mapped[str] = mapped_column(String(255))
    threshold: Mapped[int] = mapped_column(Integer)
    period: Mapped[str] = mapped_column(String(7), index=True)
    spend_usd: Mapped[float] = mapped_column(Float)
    cap_usd: Mapped[float] = mapped_column(Float)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)


class Connector(Base):
    """An MCP server from the official registry (or the playground itself), with the admin's approval decision."""

    __tablename__ = "connectors"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)  # registry name, e.g. io.github.acme/server
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[str] = mapped_column(String(64), default="")
    publisher: Mapped[str] = mapped_column(String(160), index=True)
    category: Mapped[str] = mapped_column(String(48), index=True)
    transport: Mapped[str] = mapped_column(String(16), index=True)  # remote | npm | pypi | oci | nuget | mcpb | other
    remote_url: Mapped[str] = mapped_column(String(512), default="")
    package: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    env_vars: Mapped[list[str]] = mapped_column(JSON, default=list)
    repo_url: Mapped[str] = mapped_column(String(512), default="")
    website: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(16), default="active")
    registry_updated_at: Mapped[str] = mapped_column(String(40), default="")
    signals: Mapped[int] = mapped_column(Integer, default=0)
    approval: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending | approved | blocked
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approval_note: Mapped[str] = mapped_column(String(400), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class KnowledgeSpace(Base):
    """A retrieval corpus: documents chunked and embedded with one model, visible to its owner, a department or everyone."""

    __tablename__ = "knowledge_spaces"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(400), default="")
    visibility: Mapped[str] = mapped_column(String(16), default="private")  # private | department | org
    department: Mapped[str] = mapped_column(String(128), default="General")
    embedding_model: Mapped[str] = mapped_column(String(64), default="local-hash")
    doc_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    space_id: Mapped[str] = mapped_column(String(32), ForeignKey("knowledge_spaces.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(16))  # text | file | url | dataset | repo
    source_ref: Mapped[str] = mapped_column(String(512), default="")
    bytes: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    graph: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # repository map: nodes, edges, communities
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    space_id: Mapped[str] = mapped_column(String(32), ForeignKey("knowledge_spaces.id"), index=True)
    doc_id: Mapped[str] = mapped_column(String(32), ForeignKey("knowledge_documents.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(JSON, default=list)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class ApiToken(Base):
    """Personal access token for MCP clients and scripts. Only the SHA-256 hash is stored."""

    __tablename__ = "api_tokens"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    prefix: Mapped[str] = mapped_column(String(12))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
