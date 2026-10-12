"""Add ai_settings table for CU09

Revision ID: e9c13b28f701
Revises: f508ca1a3793
Create Date: 2026-10-11 23:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e9c13b28f701"
down_revision: str | None = "f508ca1a3793"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_settings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("jury_provider", sa.String(length=50), server_default="groq", nullable=False),
        sa.Column("jury_model", sa.String(length=100), server_default="openai/gpt-oss-20b", nullable=False),
        sa.Column("jury_temperature", sa.Float(), server_default="0.2", nullable=False),
        sa.Column("jury_max_tokens", sa.Integer(), server_default="2048", nullable=False),
        sa.Column("max_followups", sa.Integer(), server_default="2", nullable=False),
        sa.Column("retrieval_top_k", sa.Integer(), server_default="4", nullable=False),
        sa.Column("evaluation_provider", sa.String(length=50), server_default="groq", nullable=False),
        sa.Column("evaluation_model", sa.String(length=100), server_default="openai/gpt-oss-20b", nullable=False),
        sa.Column("evaluation_temperature", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("fallback_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("config_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name="fk_ai_settings_updated_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ai_settings"),
    )


def downgrade() -> None:
    op.drop_table("ai_settings")
