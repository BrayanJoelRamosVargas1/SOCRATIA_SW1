"""add persisted simulation session turns

Revision ID: 20260830_0010
Revises: 20260830_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260830_0010"
down_revision: str | None = "20260830_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("simulations", sa.Column("turn_state", sa.String(length=30), nullable=True))
    op.create_check_constraint(
        "simulation_turn_state",
        "simulations",
        "turn_state IS NULL OR turn_state IN ('JURY_TURN', 'WAITING_STUDENT', 'PROCESSING')",
    )
    op.create_table(
        "simulation_turns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("simulation_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("speaker", sa.String(length=30), nullable=False),
        sa.Column("turn_type", sa.String(length=30), nullable=False),
        sa.Column("simulation_question_id", sa.String(length=36), nullable=True),
        sa.Column("question_source", sa.String(length=30), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("client_message_id", sa.String(length=36), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("sequence >= 1", name="simulation_turn_sequence"),
        sa.CheckConstraint(
            "speaker IN ('JURY', 'STUDENT', 'SYSTEM')", name="simulation_turn_speaker"
        ),
        sa.CheckConstraint(
            "turn_type IN ('QUESTION', 'ANSWER', 'FOLLOW_UP', 'EVENT')",
            name="simulation_turn_type",
        ),
        sa.CheckConstraint(
            "question_source IS NULL OR question_source IN ('BANK', 'FOLLOW_UP')",
            name="simulation_turn_question_source",
        ),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["simulation_question_id"], ["simulation_questions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_simulation_turns_simulation_id"),
        "simulation_turns",
        ["simulation_id"],
    )
    op.create_index(
        "uq_simulation_turns_sequence",
        "simulation_turns",
        ["simulation_id", "sequence"],
        unique=True,
    )
    op.create_index(
        "uq_simulation_turns_client_message",
        "simulation_turns",
        ["simulation_id", "client_message_id"],
        unique=True,
        postgresql_where=sa.text("client_message_id IS NOT NULL"),
        sqlite_where=sa.text("client_message_id IS NOT NULL"),
    )
    op.create_index(
        "uq_simulation_turns_answer_question",
        "simulation_turns",
        ["simulation_question_id"],
        unique=True,
        postgresql_where=sa.text("turn_type = 'ANSWER'"),
        sqlite_where=sa.text("turn_type = 'ANSWER'"),
    )


def downgrade() -> None:
    op.drop_index("uq_simulation_turns_answer_question", table_name="simulation_turns")
    op.drop_index("uq_simulation_turns_client_message", table_name="simulation_turns")
    op.drop_index("uq_simulation_turns_sequence", table_name="simulation_turns")
    op.drop_index(op.f("ix_simulation_turns_simulation_id"), table_name="simulation_turns")
    op.drop_table("simulation_turns")
    op.drop_constraint("simulation_turn_state", "simulations", type_="check")
    op.drop_column("simulations", "turn_state")
