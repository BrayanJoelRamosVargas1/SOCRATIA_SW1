import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.embeddings import EmbeddingError, EmbeddingProvider
from app.integrations.llm import (
    QuestionGenerationFailed,
    QuestionGenerationRequest,
    QuestionGenerationRouter,
)
from app.integrations.vector_db import VectorStoreError, VectorStoreProvider
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.exceptions import (
    DocumentNotProcessedError,
    QuestionBankNotFoundError,
    QuestionGenerationFailedError,
)
from app.modules.p2_gestion_documentos_preparacion.models.document import DocumentStatus
from app.modules.p2_gestion_documentos_preparacion.models.question_bank import QuestionBank
from app.modules.p2_gestion_documentos_preparacion.policies.document_policy import DocumentPolicy
from app.modules.p2_gestion_documentos_preparacion.repositories.document_repository import (
    DocumentRepository,
)
from app.modules.p2_gestion_documentos_preparacion.repositories.question_bank_repository import (
    GenerationState,
    QuestionBankRepository,
)
from app.modules.p2_gestion_documentos_preparacion.services.question_retrieval_service import (
    QuestionContextUnavailableError,
    QuestionRetrievalService,
)

logger = logging.getLogger(__name__)


class QuestionBankService:
    def __init__(
        self,
        *,
        db: Session,
        embeddings: EmbeddingProvider,
        vectors: VectorStoreProvider,
        generation_router: QuestionGenerationRouter,
    ) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.banks = QuestionBankRepository(db)
        self.generation_router = generation_router
        settings = get_settings()
        self.retrieval = QuestionRetrievalService(
            embeddings=embeddings,
            vectors=vectors,
            namespace_prefix=settings.pinecone_namespace_prefix,
            top_k=settings.question_retrieval_top_k,
            max_context_chars=settings.question_context_max_chars,
        )

    def generate(self, user: User, document_id: str) -> QuestionBank:
        document = DocumentPolicy.can_read(user, self.documents.get_by_id(document_id))
        if document.status != DocumentStatus.PROCESSED:
            raise DocumentNotProcessedError

        try:
            state = self.banks.start_generation(document=document)
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            logger.exception("Could not start question generation for document %s", document.id)
            raise QuestionGenerationFailedError from None

        try:
            chunks = self.retrieval.retrieve(user_id=user.id, document_id=document.id)
            result = self.generation_router.generate(
                QuestionGenerationRequest(
                    document_name=document.original_name,
                    chunks=chunks,
                )
            )
        except QuestionGenerationFailed as exc:
            reason = f"{exc.primary_failure_reason};{exc.fallback_failure_reason}"
            self._mark_failed(state, reason=reason, latency_ms=exc.latency_ms)
            raise QuestionGenerationFailedError from None
        except (EmbeddingError, VectorStoreError, QuestionContextUnavailableError):
            logger.exception("Question retrieval failed for document %s", document.id)
            self._mark_failed(state, reason="retrieval:unavailable", latency_ms=None)
            raise QuestionGenerationFailedError from None

        try:
            bank = self.banks.get_by_document(document.id, for_update=True)
            if bank is None:
                raise SQLAlchemyError("Question bank disappeared during generation")
            self.banks.complete(bank=bank, result=result)
            self.db.commit()
            self.db.refresh(bank)
            return bank
        except SQLAlchemyError:
            self.db.rollback()
            logger.exception("Could not persist question bank for document %s", document.id)
            self._mark_failed(state, reason="persistence:failed", latency_ms=result.latency_ms)
            raise QuestionGenerationFailedError from None

    def get(self, user: User, document_id: str) -> QuestionBank:
        document = DocumentPolicy.can_read(user, self.documents.get_by_id(document_id))
        bank = self.banks.get_ready_by_document(document.id)
        if bank is None:
            raise QuestionBankNotFoundError
        return bank

    def _mark_failed(
        self,
        state: GenerationState,
        *,
        reason: str,
        latency_ms: int | None,
    ) -> None:
        self.db.rollback()
        bank = self.banks.get_by_document(state.bank.document_id, for_update=True)
        if bank is None:
            logger.error("Question bank disappeared while recording a generation failure")
            return
        try:
            self.banks.mark_failed(
                bank=bank,
                had_ready_questions=state.had_ready_questions,
                reason=reason,
                latency_ms=latency_ms,
            )
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            logger.exception("Could not persist question generation failure")
