import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EvaluationStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TurnClassification(StrEnum):
    PRECISE = "PRECISE"
    INCOMPLETE = "INCOMPLETE"
    CONTRADICTORY = "CONTRADICTORY"


def enum_type(enum: type[StrEnum], name: str, length: int = 30) -> Enum:
    return Enum(
        enum,
        values_callable=lambda values: [value.value for value in values],
        native_enum=False,
        length=length,
        create_constraint=False,
        name=name,
    )


json_list_type = JSON().with_variant(JSONB(), "postgresql")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    simulation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("simulations.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    status: Mapped[EvaluationStatus] = mapped_column(
        enum_type(EvaluationStatus, "evaluation_status"),
        default=EvaluationStatus.PENDING,
        nullable=False,
    )
    evaluation_version: Mapped[str | None] = mapped_column(String(20))
    provider_used: Mapped[str | None] = mapped_column(String(50))
    model_used: Mapped[str | None] = mapped_column(String(50))

    content_score: Mapped[float | None] = mapped_column(Float)
    communication_score: Mapped[float | None] = mapped_column(Float)
    nonverbal_score: Mapped[float | None] = mapped_column(Float)
    overall_score: Mapped[float | None] = mapped_column(Float)

    failure_reason: Mapped[str | None] = mapped_column(Text)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    simulation = relationship("Simulation", lazy="selectin")
    turn_evaluations: Mapped[list["TurnEvaluation"]] = relationship(
        back_populates="evaluation", cascade="all, delete-orphan", lazy="selectin"
    )


class TurnEvaluation(Base):
    __tablename__ = "turn_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    evaluation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evaluations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    simulation_turn_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("simulation_turns.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    source_question_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("simulation_questions.id", ondelete="SET NULL")
    )

    classification: Mapped[TurnClassification | None] = mapped_column(
        enum_type(TurnClassification, "turn_classification_type")
    )
    turn_score: Mapped[float | None] = mapped_column(Float)

    strengths: Mapped[list[str]] = mapped_column(
        json_list_type, default=list, server_default=text("'[]'")
    )
    weaknesses: Mapped[list[str]] = mapped_column(
        json_list_type, default=list, server_default=text("'[]'")
    )
    missing_points: Mapped[list[str]] = mapped_column(
        json_list_type, default=list, server_default=text("'[]'")
    )
    contradictions: Mapped[list[str]] = mapped_column(
        json_list_type, default=list, server_default=text("'[]'")
    )
    evidence: Mapped[list[str]] = mapped_column(
        json_list_type, default=list, server_default=text("'[]'")
    )

    time_taken_seconds: Mapped[float | None] = mapped_column(Float)
    filler_words_count: Mapped[int | None] = mapped_column(Integer)
    eye_contact_score: Mapped[float | None] = mapped_column(Float)

    provider_used: Mapped[str | None] = mapped_column(String(50))
    model_used: Mapped[str | None] = mapped_column(String(50))
    evaluation_version: Mapped[str | None] = mapped_column(String(20))

    evaluation: Mapped[Evaluation] = relationship(back_populates="turn_evaluations")
    simulation_turn = relationship("SimulationTurn", lazy="selectin")
    source_question = relationship("SimulationQuestion", lazy="selectin")
