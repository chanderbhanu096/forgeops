"""SQLAlchemy ORM models for all ForgeOps entities."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB as _PGjsonb  # noqa: N811
from sqlalchemy.dialects.postgresql import UUID as _PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import String as SaString
from sqlalchemy.types import TypeDecorator

from forgeops.db import Base


class _JSONB(TypeDecorator[Any]):
    """JSONB on PostgreSQL, JSON on everything else."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: object) -> object:  # type: ignore[override]
        if getattr(dialect, "name", None) == "postgresql":
            return dialect.type_descriptor(_PGjsonb())  # type: ignore[union-attr]
        return dialect.type_descriptor(JSON())  # type: ignore[union-attr]


class _UUID(TypeDecorator[uuid.UUID]):
    """Native UUID on PostgreSQL, String(36) on SQLite."""

    impl = SaString(36)
    cache_ok = True

    def load_dialect_impl(self, dialect: object) -> object:  # type: ignore[override]
        if getattr(dialect, "name", None) == "postgresql":
            return dialect.type_descriptor(_PGUUID(as_uuid=True))  # type: ignore[union-attr]
        return dialect.type_descriptor(SaString(36))  # type: ignore[union-attr]

    def process_bind_param(  # type: ignore[override]
        self, value: uuid.UUID | str | None, dialect: object
    ) -> str | uuid.UUID | None:
        if value is None:
            return None
        if getattr(dialect, "name", None) == "postgresql":
            return value
        return str(value)

    def process_result_value(  # type: ignore[override]
        self, value: str | uuid.UUID | None, dialect: object
    ) -> uuid.UUID | None:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


try:
    from pgvector.sqlalchemy import Vector as _Vector

    _VECTOR_AVAILABLE = True
except ImportError:
    _VECTOR_AVAILABLE = False
    _Vector = None  # type: ignore[assignment]


def _vector_column(dims: int) -> Mapped[list[float] | None]:  # type: ignore[return-value]
    if _VECTOR_AVAILABLE and _Vector is not None:
        return mapped_column(_Vector(dims), nullable=True)
    return mapped_column(JSON, nullable=True)


class MissionStatus(StrEnum):
    pending = "pending"
    running = "running"
    paused = "paused"
    awaiting_approval = "awaiting_approval"
    approved = "approved"
    rejected = "rejected"
    completed = "completed"
    failed = "failed"
    rolled_back = "rolled_back"


class AgentState(StrEnum):
    mission_received = "mission_received"
    environment_discovery = "environment_discovery"
    plan_generation = "plan_generation"
    evidence_collection = "evidence_collection"
    hypothesis_creation = "hypothesis_creation"
    hypothesis_verification = "hypothesis_verification"
    solution_generation = "solution_generation"
    sandbox_execution = "sandbox_execution"
    test_and_review = "test_and_review"
    human_approval = "human_approval"
    execution = "execution"
    post_action_monitoring = "post_action_monitoring"
    completed = "completed"
    failed = "failed"


class ApprovalDecision(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    auto_approved = "auto_approved"


class MemoryType(StrEnum):
    episodic = "episodic"
    semantic = "semantic"
    procedural = "procedural"
    feedback = "feedback"


class ToolCallStatus(StrEnum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    blocked = "blocked"


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[uuid.UUID] = mapped_column(
        _UUID(), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # The provider/model are stored per mission so different concurrent missions
    # can safely use different LLMs.
    llm_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="demo"
    )
    llm_model: Mapped[str] = mapped_column(
        String(200), nullable=False, default="forgeops-demo"
    )

    status: Mapped[MissionStatus] = mapped_column(
        SAEnum(MissionStatus, name="mission_status"),
        nullable=False,
        default=MissionStatus.pending,
    )
    current_state: Mapped[AgentState | None] = mapped_column(
        SAEnum(AgentState, name="agent_state"), nullable=True
    )

    max_steps: Mapped[int] = mapped_column(Integer, default=50)
    steps_used: Mapped[int] = mapped_column(Integer, default=0)
    max_cost_usd: Mapped[float] = mapped_column(Float, default=2.0)
    cost_usd_used: Mapped[float] = mapped_column(Float, default=0.0)
    max_duration_seconds: Mapped[int] = mapped_column(Integer, default=600)

    checkpoint: Mapped[dict[str, Any] | None] = mapped_column(_JSONB(), nullable=True)

    attachments: Mapped[list[dict[str, Any]]] = mapped_column(
        _JSONB(), default=list, nullable=False
    )

    result: Mapped[dict[str, Any] | None] = mapped_column(_JSONB(), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    state_transitions: Mapped[list[StateTransition]] = relationship(
        back_populates="mission", cascade="all, delete-orphan", lazy="selectin"
    )
    tool_calls: Mapped[list[ToolCall]] = relationship(
        back_populates="mission", cascade="all, delete-orphan", lazy="noload"
    )
    approvals: Mapped[list[Approval]] = relationship(
        back_populates="mission", cascade="all, delete-orphan", lazy="selectin"
    )
    memory_entries: Mapped[list[MemoryEntry]] = relationship(
        back_populates="mission", cascade="all, delete-orphan", lazy="noload"
    )

    __table_args__ = (
        Index("ix_missions_status", "status"),
        Index("ix_missions_created_at", "created_at"),
    )


class StateTransition(Base):
    """Immutable audit log of every state machine transition."""

    __tablename__ = "state_transitions"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    mission_id: Mapped[uuid.UUID] = mapped_column(
        _UUID(), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
    )
    from_state: Mapped[AgentState | None] = mapped_column(
        SAEnum(AgentState, name="agent_state"), nullable=True
    )
    to_state: Mapped[AgentState] = mapped_column(
        SAEnum(AgentState, name="agent_state"), nullable=False
    )
    trigger: Mapped[str | None] = mapped_column(String(200), nullable=True)
    extra: Mapped[dict[str, Any]] = mapped_column(
        "metadata", _JSONB(), default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    mission: Mapped[Mission] = relationship(back_populates="state_transitions")

    __table_args__ = (Index("ix_state_transitions_mission_id", "mission_id"),)


class ToolCall(Base):
    """Record of every MCP tool invocation."""

    __tablename__ = "tool_calls"

    id: Mapped[uuid.UUID] = mapped_column(
        _UUID(), primary_key=True, default=uuid.uuid4
    )
    mission_id: Mapped[uuid.UUID] = mapped_column(
        _UUID(), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
    )

    tool_name: Mapped[str] = mapped_column(String(200), nullable=False)
    server: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[ToolCallStatus] = mapped_column(
        SAEnum(ToolCallStatus, name="tool_call_status"),
        nullable=False,
        default=ToolCallStatus.pending,
    )

    input: Mapped[dict[str, Any]] = mapped_column(_JSONB(), default=dict, nullable=False)
    output: Mapped[dict[str, Any] | None] = mapped_column(_JSONB(), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    mission: Mapped[Mission] = relationship(back_populates="tool_calls")

    __table_args__ = (
        Index("ix_tool_calls_mission_id", "mission_id"),
        Index("ix_tool_calls_tool_name", "tool_name"),
    )


class Skill(Base):
    """Versioned skill definitions loaded from YAML registry."""

    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        _UUID(), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    spec: Mapped[dict[str, Any]] = mapped_column(_JSONB(), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_skills_name_version", "name", "version", unique=True),
    )


class MemoryEntry(Base):
    """Long-term operational memory persisted across missions."""

    __tablename__ = "memory_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        _UUID(), primary_key=True, default=uuid.uuid4
    )
    mission_id: Mapped[uuid.UUID | None] = mapped_column(
        _UUID(), ForeignKey("missions.id", ondelete="SET NULL"), nullable=True
    )
    memory_type: Mapped[MemoryType] = mapped_column(
        SAEnum(MemoryType, name="memory_type"), nullable=False
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    extra: Mapped[dict[str, Any]] = mapped_column(
        "metadata", _JSONB(), default=dict, nullable=False
    )

    embedding: Mapped[list[float] | None] = _vector_column(1536)

    usefulness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    retrieval_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    mission: Mapped[Mission | None] = relationship(back_populates="memory_entries")

    __table_args__ = (
        Index("ix_memory_entries_type", "memory_type"),
        Index("ix_memory_entries_mission_id", "mission_id"),
        Index(
            "ix_memory_entries_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        )
        if _VECTOR_AVAILABLE
        else Index("ix_memory_entries_embedding_skip", "content"),
    )


class Approval(Base):
    """Human-in-the-loop approval gate for a mission."""

    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(
        _UUID(), primary_key=True, default=uuid.uuid4
    )
    mission_id: Mapped[uuid.UUID] = mapped_column(
        _UUID(), ForeignKey("missions.id", ondelete="CASCADE"), nullable=False
    )

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    diff: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(_JSONB(), default=dict, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)

    decision: Mapped[ApprovalDecision] = mapped_column(
        SAEnum(ApprovalDecision, name="approval_decision"),
        nullable=False,
        default=ApprovalDecision.pending,
    )
    reviewer_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    mission: Mapped[Mission] = relationship(back_populates="approvals")

    __table_args__ = (
        Index("ix_approvals_mission_id", "mission_id"),
        Index("ix_approvals_decision", "decision"),
    )
