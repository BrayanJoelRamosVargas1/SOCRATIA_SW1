"""add_partial_unique_index_active_subscription

Revision ID: 25940ab689a7
Revises: e9c13b28f701
Create Date: 2026-10-12 10:16:26.641110
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '25940ab689a7'
down_revision: str | None = 'e9c13b28f701'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_active_user_subscription",
        "subscriptions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
        sqlite_where=sa.text("status = 'ACTIVE'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_active_user_subscription",
        table_name="subscriptions",
    )

