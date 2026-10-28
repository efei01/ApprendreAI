"""create model_runs table

Revision ID: 0001
Revises:
Create Date: 2026-10-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("translation", sa.Text(), nullable=True),
        sa.Column("analysis", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_type", sa.String(length=50), nullable=True),
    )
    op.create_index("ix_model_runs_created_at", "model_runs", ["created_at"])
    op.create_index("ix_model_runs_prompt_version", "model_runs", ["prompt_version"])


def downgrade() -> None:
    op.drop_index("ix_model_runs_prompt_version", table_name="model_runs")
    op.drop_index("ix_model_runs_created_at", table_name="model_runs")
    op.drop_table("model_runs")
