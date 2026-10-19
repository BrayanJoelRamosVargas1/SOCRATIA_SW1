"""Durable preparation queue; stores metadata only, never prompts or provider keys."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, UniqueConstraint, text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class PreparationTask(Base):
    __tablename__ = "preparation_tasks"
    __table_args__ = (
        UniqueConstraint("user_id", "request_key", name="uq_preparation_request"),
        Index("uq_preparation_active_document", "document_id", unique=True,
              postgresql_where=text("status IN ('QUEUED','RUNNING')"),
              sqlite_where=text("status IN ('QUEUED','RUNNING')")),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="QUEUED", index=True)
    request_key: Mapped[str] = mapped_column(String(36))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=15)
    regenerate: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    elapsed_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
