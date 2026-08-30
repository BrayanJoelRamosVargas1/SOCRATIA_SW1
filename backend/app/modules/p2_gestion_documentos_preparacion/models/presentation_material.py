import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PresentationMaterialStatus(StrEnum):
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"


presentation_status_type = Enum(
    PresentationMaterialStatus,
    values_callable=lambda values: [value.value for value in values],
    native_enum=False,
    length=20,
    create_constraint=False,
    name="presentation_material_status",
)
json_list_type = JSON().with_variant(JSONB(), "postgresql")


class PresentationMaterial(Base):
    __tablename__ = "presentation_materials"
    __table_args__ = (
        UniqueConstraint("document_id", name="uq_presentation_materials_document_id"),
        CheckConstraint(
            "status IN ('GENERATING', 'READY', 'FAILED')",
            name="presentation_material_status",
        ),
        CheckConstraint("duration_minutes >= 5 AND duration_minutes <= 30", name="duration_range"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(200))
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    target_word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PresentationMaterialStatus] = mapped_column(
        presentation_status_type,
        default=PresentationMaterialStatus.GENERATING,
        nullable=False,
    )
    provider_used: Mapped[str | None] = mapped_column(String(30))
    model_used: Mapped[str | None] = mapped_column(String(100))
    fallback_used: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    failure_reason: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    document: Mapped["Document"] = relationship(back_populates="presentation_material")
    slides: Mapped[list["PresentationSlide"]] = relationship(
        back_populates="presentation_material",
        cascade="all, delete-orphan",
        order_by="PresentationSlide.position",
        lazy="selectin",
    )


class PresentationSlide(Base):
    __tablename__ = "presentation_slides"
    __table_args__ = (
        UniqueConstraint(
            "presentation_material_id", "position", name="uq_presentation_slides_position"
        ),
        CheckConstraint("position >= 1 AND position <= 18", name="presentation_slide_position"),
        CheckConstraint(
            "estimated_seconds >= 20 AND estimated_seconds <= 600",
            name="presentation_slide_duration",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    presentation_material_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("presentation_materials.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    objective: Mapped[str] = mapped_column(String(500), nullable=False)
    bullet_points: Mapped[list[str]] = mapped_column(json_list_type, nullable=False)
    speaker_notes: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    source_chunk_ids: Mapped[list[str]] = mapped_column(json_list_type, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    presentation_material: Mapped[PresentationMaterial] = relationship(back_populates="slides")


from app.modules.p2_gestion_documentos_preparacion.models.document import Document  # noqa: E402
