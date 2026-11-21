"""Durable bounded per-device push delivery, independently of preparation."""

import sqlalchemy as sa
from alembic import op

revision = "20261121_0017"
down_revision = "20261120_0016"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "push_deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "task_id",
            sa.String(36),
            sa.ForeignKey("preparation_tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("channel", sa.String(10), nullable=False),
        sa.Column("registration_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(40)),
        sa.UniqueConstraint(
            "task_id", "channel", "registration_id", name="uq_push_delivery_event_device"
        ),
    )
    for column in ("user_id", "status", "next_attempt_at"):
        op.create_index("ix_push_deliveries_" + column, "push_deliveries", [column])


def downgrade():
    op.drop_table("push_deliveries")
