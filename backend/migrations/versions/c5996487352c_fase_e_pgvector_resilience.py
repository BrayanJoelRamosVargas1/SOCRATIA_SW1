"""fase_e_pgvector_resilience

Revision ID: c5996487352c
Revises: a6ad5f18a9f3
Create Date: 2026-09-10 10:13:42.249940
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5996487352c'
down_revision: Union[str, None] = 'a6ad5f18a9f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Ensure the vector extension is available
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 2. Table for 768 dimension
    op.create_table(
        "vector_embeddings_768",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("embedding_space_id", sa.String(length=64), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=False),  # We'll alter this raw SQL because Alembic doesn't natively support pgvector vector types well
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["embedding_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "chunk_id", name="uq_profile_chunk_768"),
    )

    # Convert embedding column to vector(768)
    op.execute("ALTER TABLE vector_embeddings_768 ALTER COLUMN embedding TYPE vector(768) USING embedding::vector")

    # Indices for 768
    op.create_index(
        "ix_vector_embeddings_768_document_id",
        "vector_embeddings_768",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_vector_embeddings_768_user_id", "vector_embeddings_768", ["user_id"], unique=False
    )
    op.create_index(
        "ix_vector_embeddings_768_profile_id",
        "vector_embeddings_768",
        ["profile_id"],
        unique=False,
    )
    # HNSW Index
    op.execute("CREATE INDEX ix_vector_embeddings_768_embedding_hnsw ON vector_embeddings_768 USING hnsw (embedding vector_cosine_ops);")


    # 3. Table for 1024 dimension
    op.create_table(
        "vector_embeddings_1024",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("embedding_space_id", sa.String(length=64), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["embedding_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "chunk_id", name="uq_profile_chunk_1024"),
    )

    op.execute("ALTER TABLE vector_embeddings_1024 ALTER COLUMN embedding TYPE vector(1024) USING embedding::vector")

    op.create_index(
        "ix_vector_embeddings_1024_document_id",
        "vector_embeddings_1024",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_vector_embeddings_1024_user_id", "vector_embeddings_1024", ["user_id"], unique=False
    )
    op.create_index(
        "ix_vector_embeddings_1024_profile_id",
        "vector_embeddings_1024",
        ["profile_id"],
        unique=False,
    )
    # HNSW Index
    op.execute("CREATE INDEX ix_vector_embeddings_1024_embedding_hnsw ON vector_embeddings_1024 USING hnsw (embedding vector_cosine_ops);")


    # 4. Table for EmbeddingProfileStoreSync
    op.create_table(
        "embedding_profile_store_syncs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("store_name", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("vectors_expected", sa.Integer(), nullable=False),
        sa.Column("vectors_synced", sa.Integer(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_category", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["embedding_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "store_name", name="uq_profile_store_sync"),
    )
    op.create_index(
        "ix_embedding_profile_store_syncs_profile_id",
        "embedding_profile_store_syncs",
        ["profile_id"],
        unique=False,
    )

    # 5. Table for VectorSyncOutbox
    op.create_table(
        "vector_sync_outbox",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.String(length=36), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=64), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_vector_sync_outbox_profile_id", "vector_sync_outbox", ["profile_id"], unique=False
    )
    op.create_index(
        "ix_vector_sync_outbox_next_retry_at", "vector_sync_outbox", ["next_retry_at"], unique=False
    )
    op.create_index(
        "ix_vector_sync_outbox_status", "vector_sync_outbox", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_table("vector_sync_outbox")
    op.drop_table("embedding_profile_store_syncs")
    op.drop_table("vector_embeddings_1024")
    op.drop_table("vector_embeddings_768")
    op.execute("DROP EXTENSION IF EXISTS vector;")

