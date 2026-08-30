"""add P3 simulation configuration core

Revision ID: 20260830_0009
Revises: 20260830_0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260830_0009"
down_revision: str | None = "20260830_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jury_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("focus_type", sa.String(length=30), nullable=False),
        sa.Column("strictness", sa.Integer(), nullable=False),
        sa.Column("interruption_level", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "focus_type IN ('METHODOLOGICAL', 'TECHNICAL', 'CRITICAL')",
            name="jury_focus_type",
        ),
        sa.CheckConstraint(
            "interruption_level IN ('LOW', 'MEDIUM', 'HIGH')",
            name="jury_interruption_level",
        ),
        sa.CheckConstraint("strictness >= 1 AND strictness <= 5", name="jury_strictness"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "simulations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("question_bank_id", sa.String(length=36), nullable=False),
        sa.Column("jury_profile_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("planned_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("camera_ready", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("microphone_ready", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("vision_ready", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "planned_duration_minutes >= 5 AND planned_duration_minutes <= 30",
            name="simulation_duration",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'READY', 'ACTIVE', 'COMPLETED', 'ABORTED', 'ERROR')",
            name="simulation_status",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["jury_profile_id"], ["jury_profiles.id"]),
        sa.ForeignKeyConstraint(
            ["question_bank_id"], ["question_banks.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_simulations_document_id"), "simulations", ["document_id"])
    op.create_index(op.f("ix_simulations_user_id"), "simulations", ["user_id"])
    op.create_table(
        "simulation_questions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("simulation_id", sa.String(length=36), nullable=False),
        sa.Column("question_id", sa.String(length=36), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=True),
        sa.Column("asked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("position >= 0", name="simulation_question_position"),
        sa.CheckConstraint(
            "source IN ('BANK', 'FOLLOW_UP')", name="simulation_question_source"
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'ASKED', 'ANSWERED', 'SKIPPED')",
            name="simulation_question_status",
        ),
        sa.CheckConstraint(
            "(source = 'BANK' AND question_id IS NOT NULL) OR source = 'FOLLOW_UP'",
            name="simulation_question_origin",
        ),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["simulation_id"], ["simulations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "simulation_id", "position", name="uq_simulation_questions_position"
        ),
    )
    op.create_index(
        op.f("ix_simulation_questions_simulation_id"),
        "simulation_questions",
        ["simulation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_simulation_questions_simulation_id"),
        table_name="simulation_questions",
    )
    op.drop_table("simulation_questions")
    op.drop_index(op.f("ix_simulations_user_id"), table_name="simulations")
    op.drop_index(op.f("ix_simulations_document_id"), table_name="simulations")
    op.drop_table("simulations")
    op.drop_table("jury_profiles")
