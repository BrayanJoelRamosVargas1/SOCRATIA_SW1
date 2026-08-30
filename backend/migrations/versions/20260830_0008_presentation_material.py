"""add presentation materials and slides

Revision ID: 20260830_0008
Revises: 20260829_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260830_0008"
down_revision: str | None = "20260829_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "presentation_materials",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("target_word_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("provider_used", sa.String(length=30), nullable=True),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("fallback_used", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("failure_reason", sa.String(length=300), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('GENERATING', 'READY', 'FAILED')", name="presentation_material_status"
        ),
        sa.CheckConstraint(
            "duration_minutes >= 5 AND duration_minutes <= 30", name="duration_range"
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", name="uq_presentation_materials_document_id"),
    )
    op.create_index(
        op.f("ix_presentation_materials_user_id"),
        "presentation_materials",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "presentation_slides",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("presentation_material_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("objective", sa.String(length=500), nullable=False),
        sa.Column("bullet_points", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("speaker_notes", sa.Text(), nullable=False),
        sa.Column("estimated_seconds", sa.Integer(), nullable=False),
        sa.Column("source_chunk_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "estimated_seconds >= 20 AND estimated_seconds <= 600",
            name="presentation_slide_duration",
        ),
        sa.CheckConstraint("position >= 1 AND position <= 18", name="presentation_slide_position"),
        sa.ForeignKeyConstraint(
            ["presentation_material_id"], ["presentation_materials.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "presentation_material_id", "position", name="uq_presentation_slides_position"
        ),
    )
    op.create_index(
        op.f("ix_presentation_slides_presentation_material_id"),
        "presentation_slides",
        ["presentation_material_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_presentation_slides_presentation_material_id"), table_name="presentation_slides"
    )
    op.drop_table("presentation_slides")
    op.drop_index(op.f("ix_presentation_materials_user_id"), table_name="presentation_materials")
    op.drop_table("presentation_materials")
