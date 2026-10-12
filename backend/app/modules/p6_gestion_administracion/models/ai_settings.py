from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AISettings(Base):
    __tablename__ = "ai_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="default")
    jury_provider: Mapped[str] = mapped_column(String(50), default="groq", nullable=False)
    jury_model: Mapped[str] = mapped_column(
        String(100), default="openai/gpt-oss-20b", nullable=False
    )
    jury_temperature: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    jury_max_tokens: Mapped[int] = mapped_column(Integer, default=2048, nullable=False)
    max_followups: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    retrieval_top_k: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    evaluation_provider: Mapped[str] = mapped_column(String(50), default="groq", nullable=False)
    evaluation_model: Mapped[str] = mapped_column(
        String(100), default="openai/gpt-oss-20b", nullable=False
    )
    evaluation_temperature: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    fallback_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    updater = relationship("User", foreign_keys=[updated_by], lazy="selectin")
