"""Merge Fase E and P3-C migrations

Revision ID: ec1bf2da03f7
Revises: 19f41f50174a, 20260905_0012
Create Date: 2026-10-03 20:09:42.916890
"""

from collections.abc import Sequence

revision: str = "ec1bf2da03f7"
down_revision: str | None = ("19f41f50174a", "20260905_0012")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
