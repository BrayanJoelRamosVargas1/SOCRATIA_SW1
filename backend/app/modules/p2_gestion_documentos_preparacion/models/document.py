import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Computed,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    EXTRACTING = "EXTRACTING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    RETRYING = "RETRYING"
    SWITCHING_PROVIDER = "SWITCHING_PROVIDER"
    INDEXING = "INDEXING"
    PROCESSED = "PROCESSED"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"


document_status_type = Enum(
    DocumentStatus,
    values_callable=lambda values: [value.value for value in values],
    native_enum=False,
    length=20,
    create_constraint=False,
    name="document_status",
)

DOCUMENT_STATUS_CHECK = "status IN ('UPLOADED', 'QUEUED', 'EXTRACTING', 'CHUNKING', 'EMBEDDING', 'RETRYING', 'SWITCHING_PROVIDER', 'INDEXING', 'PROCESSED', 'DEGRADED', 'ERROR')"


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (CheckConstraint(DOCUMENT_STATUS_CHECK, name="document_status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(700), unique=True, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        document_status_type, default=DocumentStatus.UPLOADED, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    active_embedding_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("embedding_profiles.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )

    processing_history: Mapped[list["DocumentProcessing"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentProcessing.created_at",
        lazy="selectin",
    )
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )
    chunk_sets = relationship("ChunkSet", back_populates="document", cascade="all, delete-orphan")
    question_bank: Mapped["QuestionBank | None"] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    presentation_material: Mapped["PresentationMaterial | None"] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    embedding_profiles: Mapped[list["EmbeddingProfile"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        foreign_keys="EmbeddingProfile.document_id",
        lazy="selectin",
    )
    processing_jobs: Mapped[list["DocumentProcessingJob"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class DocumentProcessing(Base):
    __tablename__ = "document_processing"
    __table_args__ = (CheckConstraint(DOCUMENT_STATUS_CHECK, name="document_status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[DocumentStatus] = mapped_column(document_status_type, nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped[Document] = relationship(
        back_populates="processing_history", foreign_keys="DocumentProcessing.document_id"
    )


class ProfileStatus(StrEnum):
    STAGING = "STAGING"
    READY = "READY"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"
    FAILED = "FAILED"


profile_status_type = Enum(
    ProfileStatus,
    values_callable=lambda values: [value.value for value in values],
    native_enum=False,
    length=20,
    create_constraint=False,
    name="profile_status",
)


class EmbeddingProfile(Base):
    __tablename__ = "embedding_profiles"
    __table_args__ = (
        CheckConstraint(
            "status IN ('STAGING', 'READY', 'ACTIVE', 'RETIRED', 'FAILED')", name="profile_status"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chunk_set_id: Mapped[str | None] = mapped_column(
        ForeignKey("chunk_sets.id", ondelete="CASCADE"), nullable=True, index=True
    )
    status: Mapped[ProfileStatus] = mapped_column(
        profile_status_type, default=ProfileStatus.STAGING, nullable=False
    )
    embedding_space_id: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    model_revision: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_index: Mapped[str] = mapped_column(String(100), nullable=False)
    vector_namespace: Mapped[str] = mapped_column(String(200), nullable=False)
    query_prefix: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document_prefix: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped[Document] = relationship(
        back_populates="embedding_profiles", foreign_keys=[document_id]
    )
    chunk_set = relationship("ChunkSet", back_populates="embedding_profiles")


class DocumentProcessingJob(Base):
    __tablename__ = "document_processing_jobs"
    __table_args__ = (CheckConstraint(DOCUMENT_STATUS_CHECK, name="job_status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[DocumentStatus] = mapped_column(document_status_type, nullable=False)
    current_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    current_embedding_space: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chunk_set_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("chunk_sets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("embedding_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    chunks_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunks_embedded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    document: Mapped[Document] = relationship(back_populates="processing_jobs")


class ChunkSet(Base):
    __tablename__ = "chunk_sets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fingerprint = Column(String(64), nullable=False)
    chunk_size_chars = Column(Integer, nullable=False)
    chunk_overlap_chars = Column(Integer, nullable=False)
    extractor_version = Column(String(32), nullable=False, default="1.0")
    normalization_version = Column(String(32), nullable=False, default="1.0")
    chunker_version = Column(String(32), nullable=False, default="1.0")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="chunk_sets")
    chunks = relationship("DocumentChunk", back_populates="chunk_set", cascade="all, delete-orphan")
    embedding_profiles = relationship(
        "EmbeddingProfile", back_populates="chunk_set", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_set_id = Column(
        String(36), ForeignKey("chunk_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    start_char = Column(Integer, nullable=False)
    end_char = Column(Integer, nullable=False)
    search_vector = Column(
        TSVECTOR, Computed("to_tsvector('spanish', coalesce(content, ''))", persisted=True)
    )
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("chunk_set_id", "chunk_index", name="uq_chunk_set_index"),
        Index("ix_document_chunks_search_vector", "search_vector", postgresql_using="gin"),
    )

    document = relationship("Document", back_populates="chunks")
    chunk_set = relationship("ChunkSet", back_populates="chunks")


from app.modules.p2_gestion_documentos_preparacion.models.presentation_material import (  # noqa: E402
    PresentationMaterial,
)
from app.modules.p2_gestion_documentos_preparacion.models.question_bank import (  # noqa: E402
    QuestionBank,
)
