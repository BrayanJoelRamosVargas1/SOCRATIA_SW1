"""create RAG question banks

Revision ID: 20260829_0007
Revises: 20260829_0006
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260829_0007"
down_revision: str | None = "20260829_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "question_banks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("provider_used", sa.String(length=30), nullable=True),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("fallback_used", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("failure_reason", sa.String(length=300), nullable=True),
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
            "status IN ('GENERATING', 'READY', 'FAILED')",
            name=op.f("ck_question_banks_question_bank_status"),
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name=op.f("fk_question_banks_document_id_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_question_banks_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_question_banks")),
        sa.UniqueConstraint("document_id", name="uq_question_banks_document_id"),
    )
    op.create_index(
        op.f("ix_question_banks_user_id"),
        "question_banks",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "questions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("question_bank_id", sa.String(length=36), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("source_chunk_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "expected_answer_points",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "category IN ('CONCEPTUAL', 'METHODOLOGICAL', 'TECHNICAL', 'CRITICAL')",
            name=op.f("ck_questions_question_category"),
        ),
        sa.CheckConstraint(
            "difficulty IN ('MEDIUM', 'HARD')",
            name=op.f("ck_questions_question_difficulty"),
        ),
        sa.CheckConstraint(
            "position >= 0 AND position < 12",
            name=op.f("ck_questions_question_position"),
        ),
        sa.ForeignKeyConstraint(
            ["question_bank_id"],
            ["question_banks.id"],
            name=op.f("fk_questions_question_bank_id_question_banks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_questions")),
        sa.UniqueConstraint(
            "question_bank_id",
            "position",
            name="uq_questions_bank_position",
        ),
    )
    op.create_index(
        op.f("ix_questions_question_bank_id"),
        "questions",
        ["question_bank_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_questions_question_bank_id"), table_name="questions")
    op.drop_table("questions")
    op.drop_index(op.f("ix_question_banks_user_id"), table_name="question_banks")
    op.drop_table("question_banks")
