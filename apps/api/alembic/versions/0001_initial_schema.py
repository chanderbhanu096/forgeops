"""Create the initial ForgeOps database schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-03

The original repository configured Alembic but did not include any revision
files. As a result, ``alembic upgrade head`` succeeded without creating tables.

The memory embedding column is bootstrapped as JSONB so the core application can
run on PostgreSQL installations where pgvector has not been enabled yet. Vector
search already falls back to text search when the vector operator is unavailable.
A later migration can convert this column to ``vector(1536)`` after enabling the
PostgreSQL ``vector`` extension.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


MISSION_STATUS_VALUES = (
    "pending",
    "running",
    "paused",
    "awaiting_approval",
    "approved",
    "rejected",
    "completed",
    "failed",
    "rolled_back",
)

AGENT_STATE_VALUES = (
    "mission_received",
    "environment_discovery",
    "plan_generation",
    "evidence_collection",
    "hypothesis_creation",
    "hypothesis_verification",
    "solution_generation",
    "sandbox_execution",
    "test_and_review",
    "human_approval",
    "execution",
    "post_action_monitoring",
    "completed",
    "failed",
)

TOOL_CALL_STATUS_VALUES = (
    "pending",
    "running",
    "succeeded",
    "failed",
    "blocked",
)

MEMORY_TYPE_VALUES = (
    "episodic",
    "semantic",
    "procedural",
    "feedback",
)

APPROVAL_DECISION_VALUES = (
    "pending",
    "approved",
    "rejected",
    "auto_approved",
)


def _enum(values: tuple[str, ...], name: str) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()

    # Create enum types once. Column declarations below reuse them without
    # attempting to create the PostgreSQL types again.
    postgresql.ENUM(*MISSION_STATUS_VALUES, name="mission_status").create(
        bind, checkfirst=True
    )
    postgresql.ENUM(*AGENT_STATE_VALUES, name="agent_state").create(
        bind, checkfirst=True
    )
    postgresql.ENUM(*TOOL_CALL_STATUS_VALUES, name="tool_call_status").create(
        bind, checkfirst=True
    )
    postgresql.ENUM(*MEMORY_TYPE_VALUES, name="memory_type").create(
        bind, checkfirst=True
    )
    postgresql.ENUM(*APPROVAL_DECISION_VALUES, name="approval_decision").create(
        bind, checkfirst=True
    )

    existing_tables = set(sa.inspect(bind).get_table_names())

    if "missions" not in existing_tables:
        op.create_table(
            "missions",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.String(length=500), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column(
                "status",
                _enum(MISSION_STATUS_VALUES, "mission_status"),
                nullable=False,
                server_default=sa.text("'pending'"),
            ),
            sa.Column(
                "current_state",
                _enum(AGENT_STATE_VALUES, "agent_state"),
                nullable=True,
            ),
            sa.Column("max_steps", sa.Integer(), nullable=False, server_default="50"),
            sa.Column("steps_used", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "max_cost_usd", sa.Float(), nullable=False, server_default="2.0"
            ),
            sa.Column(
                "cost_usd_used", sa.Float(), nullable=False, server_default="0.0"
            ),
            sa.Column(
                "max_duration_seconds",
                sa.Integer(),
                nullable=False,
                server_default="600",
            ),
            sa.Column("checkpoint", postgresql.JSONB(), nullable=True),
            sa.Column(
                "attachments",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column("result", postgresql.JSONB(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_missions_status", "missions", ["status"], unique=False)
        op.create_index(
            "ix_missions_created_at", "missions", ["created_at"], unique=False
        )

    if "state_transitions" not in existing_tables:
        op.create_table(
            "state_transitions",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("mission_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "from_state", _enum(AGENT_STATE_VALUES, "agent_state"), nullable=True
            ),
            sa.Column(
                "to_state", _enum(AGENT_STATE_VALUES, "agent_state"), nullable=False
            ),
            sa.Column("trigger", sa.String(length=200), nullable=True),
            sa.Column(
                "metadata",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(
                ["mission_id"], ["missions.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_state_transitions_mission_id",
            "state_transitions",
            ["mission_id"],
            unique=False,
        )

    if "tool_calls" not in existing_tables:
        op.create_table(
            "tool_calls",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("mission_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("tool_name", sa.String(length=200), nullable=False),
            sa.Column("server", sa.String(length=100), nullable=False),
            sa.Column(
                "status",
                _enum(TOOL_CALL_STATUS_VALUES, "tool_call_status"),
                nullable=False,
                server_default=sa.text("'pending'"),
            ),
            sa.Column(
                "input",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("output", postgresql.JSONB(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("duration_ms", sa.Integer(), nullable=True),
            sa.Column("tokens_used", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["mission_id"], ["missions.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_tool_calls_mission_id", "tool_calls", ["mission_id"], unique=False
        )
        op.create_index(
            "ix_tool_calls_tool_name", "tool_calls", ["tool_name"], unique=False
        )

    if "skills" not in existing_tables:
        op.create_table(
            "skills",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("version", sa.String(length=20), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("spec", postgresql.JSONB(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_skills_name_version",
            "skills",
            ["name", "version"],
            unique=True,
        )

    if "memory_entries" not in existing_tables:
        op.create_table(
            "memory_entries",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("mission_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "memory_type",
                _enum(MEMORY_TYPE_VALUES, "memory_type"),
                nullable=False,
            ),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column(
                "metadata",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            # JSONB bootstrap; convert to vector(1536) in a dedicated migration
            # after enabling the PostgreSQL vector extension.
            sa.Column("embedding", postgresql.JSONB(), nullable=True),
            sa.Column(
                "usefulness_score", sa.Float(), nullable=False, server_default="0.0"
            ),
            sa.Column(
                "retrieval_count", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(
                ["mission_id"], ["missions.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_memory_entries_type",
            "memory_entries",
            ["memory_type"],
            unique=False,
        )
        op.create_index(
            "ix_memory_entries_mission_id",
            "memory_entries",
            ["mission_id"],
            unique=False,
        )

    if "approvals" not in existing_tables:
        op.create_table(
            "approvals",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("mission_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("diff", sa.Text(), nullable=True),
            sa.Column(
                "evidence",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "risk_level",
                sa.String(length=20),
                nullable=False,
                server_default="medium",
            ),
            sa.Column(
                "decision",
                _enum(APPROVAL_DECISION_VALUES, "approval_decision"),
                nullable=False,
                server_default=sa.text("'pending'"),
            ),
            sa.Column("reviewer_id", sa.String(length=200), nullable=True),
            sa.Column("reviewer_notes", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["mission_id"], ["missions.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_approvals_mission_id", "approvals", ["mission_id"], unique=False
        )
        op.create_index(
            "ix_approvals_decision", "approvals", ["decision"], unique=False
        )


def downgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())

    for table_name in (
        "approvals",
        "memory_entries",
        "skills",
        "tool_calls",
        "state_transitions",
        "missions",
    ):
        if table_name in existing_tables:
            op.drop_table(table_name)

    postgresql.ENUM(name="approval_decision").drop(bind, checkfirst=True)
    postgresql.ENUM(name="memory_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="tool_call_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="agent_state").drop(bind, checkfirst=True)
    postgresql.ENUM(name="mission_status").drop(bind, checkfirst=True)
