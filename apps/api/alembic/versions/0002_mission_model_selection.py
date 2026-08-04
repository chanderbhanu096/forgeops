"""Add per-mission LLM provider and model selection.

Revision ID: 0002_mission_model_selection
Revises: 0001_initial_schema
Create Date: 2026-08-04
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_mission_model_selection"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "missions",
        sa.Column(
            "llm_provider",
            sa.String(length=50),
            nullable=False,
            server_default="demo",
        ),
    )
    op.add_column(
        "missions",
        sa.Column(
            "llm_model",
            sa.String(length=200),
            nullable=False,
            server_default="forgeops-demo",
        ),
    )


def downgrade() -> None:
    op.drop_column("missions", "llm_model")
    op.drop_column("missions", "llm_provider")
