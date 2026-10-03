"""fase_e_5_fts

Revision ID: 20260911_0012
Revises: c5996487352c
Create Date: 2026-09-11 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '20260911_0012'
down_revision: str | None = '595f11211b53'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add search_vector column to document_chunks
    op.add_column(
        'document_chunks',
        sa.Column(
            'search_vector',
            postgresql.TSVECTOR(),
            sa.Computed(
                "to_tsvector('spanish', coalesce(content, ''))",
                persisted=True
            ),
            nullable=True
        )
    )
    
    # Create GIN index on search_vector
    op.create_index(
        'ix_document_chunks_search_vector',
        'document_chunks',
        ['search_vector'],
        unique=False,
        postgresql_using='gin'
    )


def downgrade() -> None:
    op.drop_index('ix_document_chunks_search_vector', table_name='document_chunks', postgresql_using='gin')
    op.drop_column('document_chunks', 'search_vector')
