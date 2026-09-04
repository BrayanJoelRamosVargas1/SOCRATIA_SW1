"""add voice ai session features

Revision ID: 20260904_0011
Revises: 20260830_0010
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260904_0011"
down_revision: str | None = "20260830_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. New columns for simulation_questions
    op.add_column(
        "simulation_questions", sa.Column("parent_question_id", sa.String(length=36), nullable=True)
    )
    op.add_column(
        "simulation_questions",
        sa.Column("follow_up_depth", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_foreign_key(
        "fk_simulation_questions_parent_id",
        "simulation_questions",
        "simulation_questions",
        ["parent_question_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 2. New columns for simulation_turns
    op.add_column(
        "simulation_turns",
        sa.Column("input_mode", sa.String(length=30), server_default="TEXT", nullable=False),
    )
    op.add_column(
        "simulation_turns", sa.Column("parent_turn_id", sa.String(length=36), nullable=True)
    )
    op.create_foreign_key(
        "fk_simulation_turns_parent_id",
        "simulation_turns",
        "simulation_turns",
        ["parent_turn_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(
        "simulation_turn_input_mode",
        "simulation_turns",
        "input_mode IN ('TEXT', 'VOICE')",
    )

    # 3. New table voice_utterances
    op.create_table(
        "voice_utterances",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("simulation_id", sa.String(length=36), nullable=False),
        sa.Column("turn_id", sa.String(length=36), nullable=True),
        sa.Column("client_utterance_id", sa.String(length=36), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("stt_provider", sa.String(length=50), nullable=True),
        sa.Column("stt_model", sa.String(length=100), nullable=True),
        sa.Column("stt_latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('PROCESSING', 'COMPLETED', 'ERROR')",
            name="voice_utterance_status",
        ),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["turn_id"], ["simulation_turns.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_voice_utterances_simulation_id"),
        "voice_utterances",
        ["simulation_id"],
    )
    op.create_index(
        "uq_voice_utterances_client_utterance",
        "voice_utterances",
        ["simulation_id", "client_utterance_id"],
        unique=True,
    )


def downgrade() -> None:
    # 1. Drop voice_utterances
    op.drop_index("uq_voice_utterances_client_utterance", table_name="voice_utterances")
    op.drop_index(op.f("ix_voice_utterances_simulation_id"), table_name="voice_utterances")
    op.drop_table("voice_utterances")

    # 2. Drop columns from simulation_turns
    op.drop_constraint("simulation_turn_input_mode", "simulation_turns", type_="check")
    op.drop_constraint("fk_simulation_turns_parent_id", "simulation_turns", type_="foreignkey")
    op.drop_column("simulation_turns", "parent_turn_id")
    op.drop_column("simulation_turns", "input_mode")

    # 3. Drop columns from simulation_questions
    op.drop_constraint(
        "fk_simulation_questions_parent_id", "simulation_questions", type_="foreignkey"
    )
    op.drop_column("simulation_questions", "follow_up_depth")
    op.drop_column("simulation_questions", "parent_question_id")
