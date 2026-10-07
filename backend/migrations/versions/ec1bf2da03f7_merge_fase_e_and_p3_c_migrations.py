"""Merge Fase E and P3-C migrations

Revision ID: ec1bf2da03f7
Revises: 19f41f50174a, 20260905_0012
Create Date: 2026-10-03 20:09:42.916890
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'ec1bf2da03f7'
down_revision: Union[str, None] = ('19f41f50174a', '20260905_0012')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

