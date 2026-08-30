from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.llm import GeneratedQuestionBank, QuestionGenerationResult
from app.modules.p2_gestion_documentos_preparacion.models.document import Document
from app.modules.p2_gestion_documentos_preparacion.models.question_bank import (
    Question,
    QuestionBank,
    QuestionBankStatus,
)


@dataclass(frozen=True, slots=True)
class GenerationState:
    bank: QuestionBank
    had_ready_questions: bool


class QuestionBankRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_document(self, document_id: str, *, for_update: bool = False) -> QuestionBank | None:
        statement = select(QuestionBank).where(QuestionBank.document_id == document_id)
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalars(statement).unique().one_or_none()

    def get_ready_by_document(self, document_id: str) -> QuestionBank | None:
        statement = select(QuestionBank).where(
            QuestionBank.document_id == document_id,
            QuestionBank.status == QuestionBankStatus.READY,
        )
        return self.db.scalars(statement).unique().one_or_none()

    def start_generation(self, *, document: Document) -> GenerationState:
        bank = self.get_by_document(document.id, for_update=True)
        if bank is None:
            bank = QuestionBank(
                document_id=document.id,
                user_id=document.user_id,
                status=QuestionBankStatus.GENERATING,
            )
            self.db.add(bank)
            self.db.flush()
            return GenerationState(bank=bank, had_ready_questions=False)

        had_ready_questions = bank.status == QuestionBankStatus.READY and bool(bank.questions)
        bank.status = QuestionBankStatus.GENERATING
        bank.failure_reason = None
        self.db.flush()
        return GenerationState(bank=bank, had_ready_questions=had_ready_questions)

    def complete(self, *, bank: QuestionBank, result: QuestionGenerationResult) -> None:
        bank.questions.clear()
        self.db.flush()
        bank.questions.extend(self._questions(bank, result.bank))
        bank.status = QuestionBankStatus.READY
        bank.provider_used = result.provider
        bank.model_used = result.model
        bank.fallback_used = result.fallback_used
        bank.latency_ms = result.latency_ms
        bank.failure_reason = result.primary_failure_reason
        self.db.flush()

    def mark_failed(
        self,
        *,
        bank: QuestionBank,
        had_ready_questions: bool,
        reason: str,
        latency_ms: int | None,
    ) -> None:
        bank.status = (
            QuestionBankStatus.READY if had_ready_questions else QuestionBankStatus.FAILED
        )
        bank.failure_reason = reason[:300]
        bank.latency_ms = latency_ms
        self.db.flush()

    @staticmethod
    def _questions(bank: QuestionBank, generated: GeneratedQuestionBank) -> list[Question]:
        return [
            Question(
                question_bank=bank,
                question=item.question,
                category=item.category,
                difficulty=item.difficulty,
                source_chunk_ids=item.source_chunk_ids,
                expected_answer_points=item.expected_answer_points,
                position=position,
            )
            for position, item in enumerate(generated.questions)
        ]
