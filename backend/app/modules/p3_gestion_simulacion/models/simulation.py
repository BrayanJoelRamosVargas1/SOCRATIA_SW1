import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FocusType(StrEnum):
    METHODOLOGICAL = "METHODOLOGICAL"
    TECHNICAL = "TECHNICAL"
    CRITICAL = "CRITICAL"


class InterruptionLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SimulationStatus(StrEnum):
    DRAFT = "DRAFT"
    READY = "READY"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    ERROR = "ERROR"


class SimulationQuestionStatus(StrEnum):
    PENDING = "PENDING"
    ASKED = "ASKED"
    ANSWERED = "ANSWERED"
    SKIPPED = "SKIPPED"


class SimulationQuestionSource(StrEnum):
    BANK = "BANK"
    FOLLOW_UP = "FOLLOW_UP"


def enum_type(enum: type[StrEnum], name: str, length: int = 30) -> Enum:
    return Enum(
        enum,
        values_callable=lambda values: [value.value for value in values],
        native_enum=False,
        length=length,
        create_constraint=False,
        name=name,
    )


class JuryProfile(Base):
    __tablename__ = "jury_profiles"
    __table_args__ = (
        CheckConstraint("strictness >= 1 AND strictness <= 5", name="jury_strictness"),
        CheckConstraint(
            "focus_type IN ('METHODOLOGICAL', 'TECHNICAL', 'CRITICAL')",
            name="jury_focus_type",
        ),
        CheckConstraint(
            "interruption_level IN ('LOW', 'MEDIUM', 'HIGH')",
            name="jury_interruption_level",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    focus_type: Mapped[FocusType] = mapped_column(enum_type(FocusType, "jury_focus_type"))
    strictness: Mapped[int] = mapped_column(Integer, nullable=False)
    interruption_level: Mapped[InterruptionLevel] = mapped_column(
        enum_type(InterruptionLevel, "jury_interruption_level"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Simulation(Base):
    __tablename__ = "simulations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'READY', 'ACTIVE', 'COMPLETED', 'ABORTED', 'ERROR')",
            name="simulation_status",
        ),
        CheckConstraint(
            "planned_duration_minutes >= 5 AND planned_duration_minutes <= 30",
            name="simulation_duration",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_bank_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("question_banks.id", ondelete="CASCADE"), nullable=False
    )
    jury_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jury_profiles.id"), nullable=False
    )
    status: Mapped[SimulationStatus] = mapped_column(
        enum_type(SimulationStatus, "simulation_status"),
        default=SimulationStatus.DRAFT,
        nullable=False,
    )
    planned_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    camera_ready: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    microphone_ready: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    vision_ready: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    document = relationship("Document", lazy="selectin")
    question_bank = relationship("QuestionBank", lazy="selectin")
    jury_profile: Mapped[JuryProfile] = relationship(lazy="selectin")
    questions: Mapped[list["SimulationQuestion"]] = relationship(
        back_populates="simulation",
        cascade="all, delete-orphan",
        order_by="SimulationQuestion.position",
        lazy="selectin",
    )

    @property
    def question_count(self) -> int:
        return len(self.questions)


class SimulationQuestion(Base):
    __tablename__ = "simulation_questions"
    __table_args__ = (
        UniqueConstraint("simulation_id", "position", name="uq_simulation_questions_position"),
        CheckConstraint("position >= 0", name="simulation_question_position"),
        CheckConstraint(
            "status IN ('PENDING', 'ASKED', 'ANSWERED', 'SKIPPED')",
            name="simulation_question_status",
        ),
        CheckConstraint("source IN ('BANK', 'FOLLOW_UP')", name="simulation_question_source"),
        CheckConstraint(
            "(source = 'BANK' AND question_id IS NOT NULL) OR source = 'FOLLOW_UP'",
            name="simulation_question_origin",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    simulation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("simulations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("questions.id", ondelete="SET NULL")
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[SimulationQuestionSource] = mapped_column(
        enum_type(SimulationQuestionSource, "simulation_question_source"), nullable=False
    )
    status: Mapped[SimulationQuestionStatus] = mapped_column(
        enum_type(SimulationQuestionStatus, "simulation_question_status"), nullable=False
    )
    prompt_text: Mapped[str | None] = mapped_column(Text)
    asked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    simulation: Mapped[Simulation] = relationship(back_populates="questions")
    question = relationship("Question", lazy="joined")


from app.modules.p2_gestion_documentos_preparacion.models.document import (  # noqa: E402,F401
    Document,
)
from app.modules.p2_gestion_documentos_preparacion.models.question_bank import (  # noqa: E402,F401
    Question,
    QuestionBank,
)
