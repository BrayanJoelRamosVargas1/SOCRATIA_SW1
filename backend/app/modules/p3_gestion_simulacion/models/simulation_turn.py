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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.p3_gestion_simulacion.models.simulation import (
    SimulationQuestionSource,
    enum_type,
)


class SimulationTurnSpeaker(StrEnum):
    JURY = "JURY"
    STUDENT = "STUDENT"
    SYSTEM = "SYSTEM"


class SimulationTurnType(StrEnum):
    QUESTION = "QUESTION"
    ANSWER = "ANSWER"
    FOLLOW_UP = "FOLLOW_UP"
    EVENT = "EVENT"


class SimulationTurnInputMode(StrEnum):
    TEXT = "TEXT"
    VOICE = "VOICE"


class SimulationTurn(Base):
    __tablename__ = "simulation_turns"
    __table_args__ = (
        CheckConstraint("sequence >= 1", name="simulation_turn_sequence"),
        CheckConstraint("speaker IN ('JURY', 'STUDENT', 'SYSTEM')", name="simulation_turn_speaker"),
        CheckConstraint(
            "turn_type IN ('QUESTION', 'ANSWER', 'FOLLOW_UP', 'EVENT')",
            name="simulation_turn_type",
        ),
        CheckConstraint(
            "question_source IS NULL OR question_source IN ('BANK', 'FOLLOW_UP')",
            name="simulation_turn_question_source",
        ),
        CheckConstraint(
            "input_mode IN ('TEXT', 'VOICE')",
            name="simulation_turn_input_mode",
        ),
        Index(
            "uq_simulation_turns_sequence",
            "simulation_id",
            "sequence",
            unique=True,
        ),
        Index(
            "uq_simulation_turns_client_message",
            "simulation_id",
            "client_message_id",
            unique=True,
            postgresql_where=text("client_message_id IS NOT NULL"),
            sqlite_where=text("client_message_id IS NOT NULL"),
        ),
        Index(
            "uq_simulation_turns_answer_question",
            "simulation_question_id",
            unique=True,
            postgresql_where=text("turn_type = 'ANSWER'"),
            sqlite_where=text("turn_type = 'ANSWER'"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    simulation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("simulations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[SimulationTurnSpeaker] = mapped_column(
        enum_type(SimulationTurnSpeaker, "simulation_turn_speaker"), nullable=False
    )
    turn_type: Mapped[SimulationTurnType] = mapped_column(
        enum_type(SimulationTurnType, "simulation_turn_type"), nullable=False
    )
    simulation_question_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("simulation_questions.id", ondelete="SET NULL"), nullable=True
    )
    question_source: Mapped[SimulationQuestionSource | None] = mapped_column(
        enum_type(SimulationQuestionSource, "simulation_turn_question_source"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    client_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    input_mode: Mapped[SimulationTurnInputMode] = mapped_column(
        enum_type(SimulationTurnInputMode, "simulation_turn_input_mode"),
        default=SimulationTurnInputMode.TEXT,
        nullable=False,
    )
    parent_turn_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("simulation_turns.id", ondelete="CASCADE"), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    simulation = relationship("Simulation", back_populates="turns")
    simulation_question = relationship("SimulationQuestion", lazy="joined")
    parent_turn = relationship("SimulationTurn", remote_side=[id], lazy="selectin")
