import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    ERROR = "ERROR"


document_status_type = Enum(
    DocumentStatus,
    values_callable=lambda values: [value.value for value in values],
    native_enum=False,
    length=20,
    create_constraint=False,
    name="document_status",
)

DOCUMENT_STATUS_CHECK = "status IN ('UPLOADED', 'PROCESSING', 'PROCESSED', 'ERROR')"


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

    processing_history: Mapped[list["DocumentProcessing"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentProcessing.created_at",
        lazy="selectin",
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
        lazy="selectin",
    )
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

    document: Mapped[Document] = relationship(back_populates="processing_history")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_chunk_position",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    start_char: Mapped[int] = mapped_column(Integer, nullable=False)
    end_char: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped[Document] = relationship(back_populates="chunks")


from app.modules.p2_gestion_documentos_preparacion.models.presentation_material import (  # noqa: E402
    PresentationMaterial,
)
from app.modules.p2_gestion_documentos_preparacion.models.question_bank import (  # noqa: E402
    QuestionBank,
)
