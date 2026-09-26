"""fase_e_1_5_chunk_sets

Revision ID: 595f11211b53
Revises: c5996487352c
Create Date: 2026-09-10 10:18:16.308348
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '595f11211b53'
down_revision: Union[str, None] = 'c5996487352c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


import uuid
def upgrade() -> None:
    # 0. Update DocumentStatus constraints
    op.drop_constraint("document_status", "documents", type_="check")
    op.create_check_constraint("document_status", "documents", "status IN ('UPLOADED', 'QUEUED', 'EXTRACTING', 'CHUNKING', 'EMBEDDING', 'RETRYING', 'SWITCHING_PROVIDER', 'INDEXING', 'PROCESSED', 'DEGRADED', 'ERROR')")

    op.drop_constraint("document_status", "document_processing", type_="check")
    op.create_check_constraint("document_status", "document_processing", "status IN ('UPLOADED', 'QUEUED', 'EXTRACTING', 'CHUNKING', 'EMBEDDING', 'RETRYING', 'SWITCHING_PROVIDER', 'INDEXING', 'PROCESSED', 'DEGRADED', 'ERROR')")

    # 1. Create chunk_sets table
    op.create_table(
        "chunk_sets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("chunk_size_chars", sa.Integer(), nullable=False),
        sa.Column("chunk_overlap_chars", sa.Integer(), nullable=False),
        sa.Column("extractor_version", sa.String(length=32), nullable=False),
        sa.Column("normalization_version", sa.String(length=32), nullable=False),
        sa.Column("chunker_version", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chunk_sets_document_id", "chunk_sets", ["document_id"], unique=False)

    # 2. Add content_hash to documents
    op.add_column("documents", sa.Column("content_hash", sa.String(length=64), nullable=True))

    # 3. Add chunk_set_id to document_chunks, embedding_profiles, and document_processing_jobs
    op.add_column("document_chunks", sa.Column("chunk_set_id", sa.String(length=36), nullable=True))
    op.add_column("embedding_profiles", sa.Column("chunk_set_id", sa.String(length=36), nullable=True))
    op.add_column("document_processing_jobs", sa.Column("chunk_set_id", sa.String(length=36), nullable=True))
    op.add_column("document_processing_jobs", sa.Column("profile_id", sa.String(length=36), nullable=True))
    
    # 3. Data migration: create a legacy ChunkSet for each existing document
    # and link existing chunks and profiles to it.
    connection = op.get_bind()
    documents = connection.execute(sa.text("SELECT id FROM documents")).fetchall()
    
    for doc in documents:
        doc_id = doc[0]
        chunk_set_id = str(uuid.uuid4())
        
        # We assume default values for legacy chunk sets
        connection.execute(
            sa.text("""
                INSERT INTO chunk_sets (id, document_id, fingerprint, chunk_size_chars, chunk_overlap_chars, extractor_version, normalization_version, chunker_version, created_at)
                VALUES (:id, :doc_id, :fingerprint, 3000, 400, 'legacy', 'legacy', 'legacy', now())
            """),
            {"id": chunk_set_id, "doc_id": doc_id, "fingerprint": f"legacy_{doc_id}"}
        )
        
        # Link chunks
        connection.execute(
            sa.text("UPDATE document_chunks SET chunk_set_id = :cs_id WHERE document_id = :doc_id"),
            {"cs_id": chunk_set_id, "doc_id": doc_id}
        )
        
        # Link profiles
        connection.execute(
            sa.text("UPDATE embedding_profiles SET chunk_set_id = :cs_id WHERE document_id = :doc_id"),
            {"cs_id": chunk_set_id, "doc_id": doc_id}
        )

        # Set default content_hash for legacy documents
        connection.execute(
            sa.text("UPDATE documents SET content_hash = :hash WHERE id = :doc_id"),
            {"hash": f"legacy_hash_{doc_id}", "doc_id": doc_id}
        )

    # 4. Make fields non-nullable where necessary
    op.alter_column("documents", "content_hash", existing_type=sa.String(length=64), nullable=False)

    op.alter_column("document_chunks", "chunk_set_id", existing_type=sa.String(length=36), nullable=False)
    op.create_index("ix_document_chunks_chunk_set_id", "document_chunks", ["chunk_set_id"], unique=False)
    op.create_foreign_key(
        "fk_document_chunks_chunk_set_id", "document_chunks", "chunk_sets", ["chunk_set_id"], ["id"], ondelete="CASCADE"
    )

    op.alter_column("embedding_profiles", "chunk_set_id", existing_type=sa.String(length=36), nullable=False)
    op.create_index("ix_embedding_profiles_chunk_set_id", "embedding_profiles", ["chunk_set_id"], unique=False)
    op.create_foreign_key(
        "fk_embedding_profiles_chunk_set_id", "embedding_profiles", "chunk_sets", ["chunk_set_id"], ["id"], ondelete="CASCADE"
    )

    op.create_index("ix_document_processing_jobs_chunk_set_id", "document_processing_jobs", ["chunk_set_id"], unique=False)
    op.create_foreign_key(
        "fk_document_processing_jobs_chunk_set_id", "document_processing_jobs", "chunk_sets", ["chunk_set_id"], ["id"], ondelete="SET NULL"
    )

    op.create_index("ix_document_processing_jobs_profile_id", "document_processing_jobs", ["profile_id"], unique=False)
    op.create_foreign_key(
        "fk_document_processing_jobs_profile_id", "document_processing_jobs", "embedding_profiles", ["profile_id"], ["id"], ondelete="SET NULL"
    )
    
    # 5. Drop old unique constraint and create new one for chunks
    op.drop_constraint("uq_document_chunks_document_chunk_position", "document_chunks", type_="unique")
    op.create_unique_constraint("uq_chunk_set_index", "document_chunks", ["chunk_set_id", "chunk_index"])


def downgrade() -> None:
    op.drop_constraint("uq_chunk_set_index", "document_chunks", type_="unique")
    op.create_unique_constraint("uq_document_chunks_document_chunk_position", "document_chunks", ["document_id", "chunk_index"])
    
    op.drop_constraint("fk_embedding_profiles_chunk_set_id", "embedding_profiles", type_="foreignkey")
    op.drop_index("ix_embedding_profiles_chunk_set_id", table_name="embedding_profiles")
    op.drop_column("embedding_profiles", "chunk_set_id")
    
    op.drop_constraint("fk_document_chunks_chunk_set_id", "document_chunks", type_="foreignkey")
    op.drop_index("ix_document_chunks_chunk_set_id", table_name="document_chunks")
    op.drop_column("document_chunks", "chunk_set_id")

    op.drop_constraint("fk_document_processing_jobs_chunk_set_id", "document_processing_jobs", type_="foreignkey")
    op.drop_index("ix_document_processing_jobs_chunk_set_id", table_name="document_processing_jobs")
    op.drop_column("document_processing_jobs", "chunk_set_id")
    op.drop_constraint("document_status", "documents", type_="check")
    op.create_check_constraint("document_status", "documents", "status IN ('UPLOADED', 'PROCESSING', 'PROCESSED', 'ERROR')")

    op.drop_constraint("document_status", "document_processing", type_="check")
    op.create_check_constraint("document_status", "document_processing", "status IN ('UPLOADED', 'PROCESSING', 'PROCESSED', 'ERROR')")
    op.drop_constraint("fk_document_processing_jobs_profile_id", "document_processing_jobs", type_="foreignkey")
    op.drop_index("ix_document_processing_jobs_profile_id", table_name="document_processing_jobs")
    op.drop_column("document_processing_jobs", "profile_id")

    op.drop_column("documents", "content_hash")
    
    op.drop_index("ix_chunk_sets_document_id", table_name="chunk_sets")
    op.drop_table("chunk_sets")

