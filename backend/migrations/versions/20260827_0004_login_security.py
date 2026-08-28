"""add progressive login protection and authentication events

Revision ID: 20260827_0004
Revises: 20260826_0003
Create Date: 2026-08-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260827_0004"
down_revision: str | None = "20260826_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "login_security",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("lock_level", sa.Integer(), server_default="0", nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_login_security_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_security")),
        sa.UniqueConstraint("user_id", name=op.f("uq_login_security_user_id")),
    )
    op.create_table(
        "authentication_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("identifier_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_authentication_events_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_authentication_events")),
    )
    op.create_index(
        "ix_authentication_events_created_at",
        "authentication_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_authentication_events_event_type_created_at",
        "authentication_events",
        ["event_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_authentication_events_ip_created_at",
        "authentication_events",
        ["ip_address", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_authentication_events_user_created_at",
        "authentication_events",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_authentication_events_user_created_at",
        table_name="authentication_events",
    )
    op.drop_index(
        "ix_authentication_events_ip_created_at",
        table_name="authentication_events",
    )
    op.drop_index(
        "ix_authentication_events_event_type_created_at",
        table_name="authentication_events",
    )
    op.drop_index(
        "ix_authentication_events_created_at",
        table_name="authentication_events",
    )
    op.drop_table("authentication_events")
    op.drop_table("login_security")
