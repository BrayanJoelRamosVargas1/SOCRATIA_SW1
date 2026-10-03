import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from app.core.database import Base

if TYPE_CHECKING:
    pass


class VectorEmbedding768(Base):
    __tablename__ = "vector_embeddings_768"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(
        String(36),
        ForeignKey("embedding_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id = Column(
        String(36), ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False
    )
    document_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    embedding_space_id = Column(String(64), nullable=False)
    # The true type is vector(768), but we map it as Text or a custom type in SQLAlchemy. We'll use Text for now and cast.
    embedding = Column(Text, nullable=False)

    from sqlalchemy import func
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("profile_id", "chunk_id", name="uq_profile_chunk_768"),)


class VectorEmbedding1024(Base):
    __tablename__ = "vector_embeddings_1024"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(
        String(36),
        ForeignKey("embedding_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_id = Column(
        String(36), ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False
    )
    document_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    embedding_space_id = Column(String(64), nullable=False)
    embedding = Column(Text, nullable=False)

    from sqlalchemy import func
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("profile_id", "chunk_id", name="uq_profile_chunk_1024"),)


class EmbeddingProfileStoreSync(Base):
    __tablename__ = "embedding_profile_store_syncs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(
        String(36),
        ForeignKey("embedding_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    store_name = Column(String(32), nullable=False)  # e.g. "pinecone", "pgvector"

    status = Column(
        String(32), nullable=False, default="PENDING"
    )  # PENDING, SYNCING, SYNCED, RETRYING, ERROR
    vectors_expected = Column(Integer, nullable=False, default=0)
    vectors_synced = Column(Integer, nullable=False, default=0)

    attempt_count = Column(Integer, nullable=False, default=0)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    last_error_category = Column(String(64), nullable=True)
    last_error = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    __table_args__ = (UniqueConstraint("profile_id", "store_name", name="uq_profile_store_sync"),)


class VectorSyncOutbox(Base):
    __tablename__ = "vector_sync_outbox"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String(36), nullable=False, index=True)
    chunk_id = Column(String(36), nullable=False)
    dimension = Column(Integer, nullable=False)
    operation = Column(String(16), nullable=False, default="UPSERT")  # UPSERT, DELETE
    target_namespace = Column(String(200), nullable=True)
    target_index = Column(String(100), nullable=True)

    attempts = Column(Integer, nullable=False, default=0)
    next_retry_at = Column(DateTime(timezone=True), nullable=True, index=True)
    status = Column(
        String(32), nullable=False, default="PENDING", index=True
    )  # PENDING, RETRYING, COMPLETED, ERROR

    locked_at = Column(DateTime(timezone=True), nullable=True)
    locked_by = Column(String(64), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
