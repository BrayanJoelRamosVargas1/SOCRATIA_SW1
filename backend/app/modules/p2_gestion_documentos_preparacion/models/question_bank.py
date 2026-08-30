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
from app.integrations.llm.base import QuestionCategory, QuestionDifficulty


class QuestionBankStatus(StrEnum):
    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"


question_bank_status_type = Enum(
    QuestionBankStatus,
    values_callable=lambda values: [value.value for value in values],
    native_enum=False,
    length=20,
    create_constraint=False,
    name="question_bank_status",
)
question_category_type = Enum(
    QuestionCategory,
    values_callable=lambda values: [value.value for value in values],
    native_enum=False,
    length=20,
    create_constraint=False,
    name="question_category",
)
question_difficulty_type = Enum(
    QuestionDifficulty,
    values_callable=lambda values: [value.value for value in values],
    native_enum=False,
    length=20,
    create_constraint=False,
    name="question_difficulty",
)
json_list_type = JSON().with_variant(JSONB(), "postgresql")


class QuestionBank(Base):
    __tablename__ = "question_banks"
    __table_args__ = (
        UniqueConstraint("document_id", name="uq_question_banks_document_id"),
        CheckConstraint(
            "status IN ('GENERATING', 'READY', 'FAILED')",
            name="question_bank_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[QuestionBankStatus] = mapped_column(
        question_bank_status_type,
        default=QuestionBankStatus.GENERATING,
        nullable=False,
    )
    provider_used: Mapped[str | None] = mapped_column(String(30))
    model_used: Mapped[str | None] = mapped_column(String(100))
    fallback_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    failure_reason: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    document: Mapped["Document"] = relationship(back_populates="question_bank")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="question_bank",
        cascade="all, delete-orphan",
        order_by="Question.position",
        lazy="selectin",
    )


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint(
            "question_bank_id",
            "position",
            name="uq_questions_bank_position",
        ),
        CheckConstraint(
            "category IN ('CONCEPTUAL', 'METHODOLOGICAL', 'TECHNICAL', 'CRITICAL')",
            name="question_category",
        ),
        CheckConstraint(
            "difficulty IN ('MEDIUM', 'HARD')",
            name="question_difficulty",
        ),
        CheckConstraint("position >= 0 AND position < 12", name="question_position"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_bank_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("question_banks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[QuestionCategory] = mapped_column(question_category_type, nullable=False)
    difficulty: Mapped[QuestionDifficulty] = mapped_column(
        question_difficulty_type,
        nullable=False,
    )
    source_chunk_ids: Mapped[list[str]] = mapped_column(json_list_type, nullable=False)
    expected_answer_points: Mapped[list[str]] = mapped_column(json_list_type, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    question_bank: Mapped[QuestionBank] = relationship(back_populates="questions")


from app.modules.p2_gestion_documentos_preparacion.models.document import Document  # noqa: E402
