import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.p3_gestion_simulacion.models.simulation import enum_type


class VoiceUtteranceStatus(StrEnum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class VoiceUtterance(Base):
    __tablename__ = "voice_utterances"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PROCESSING', 'COMPLETED', 'ERROR')",
            name="voice_utterance_status",
        ),
        Index(
            "uq_voice_utterances_client_utterance",
            "simulation_id",
            "client_utterance_id",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    simulation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("simulations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    turn_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("simulation_turns.id", ondelete="SET NULL"), nullable=True
    )
    client_utterance_id: Mapped[str] = mapped_column(String(36), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[VoiceUtteranceStatus] = mapped_column(
        enum_type(VoiceUtteranceStatus, "voice_utterance_status"), nullable=False
    )
    stt_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    stt_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stt_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stt_fallback_used: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    raw_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    simulation = relationship("Simulation", lazy="selectin")
    turn = relationship("SimulationTurn", lazy="selectin")
