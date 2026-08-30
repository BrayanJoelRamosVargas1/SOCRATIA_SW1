import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.embeddings import EmbeddingError, EmbeddingProvider
from app.integrations.llm.presentation import (
    PresentationGenerationFailed,
    PresentationGenerationRequest,
)
from app.integrations.llm.presentation_router import PresentationGenerationRouter
from app.integrations.vector_db import VectorStoreError, VectorStoreProvider
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.exceptions import (
    DocumentNotProcessedError,
    PresentationGenerationFailedError,
    PresentationMaterialAlreadyExistsError,
    PresentationMaterialNotFoundError,
)
from app.modules.p2_gestion_documentos_preparacion.models.document import DocumentStatus
from app.modules.p2_gestion_documentos_preparacion.models.presentation_material import (
    PresentationMaterial,
)
from app.modules.p2_gestion_documentos_preparacion.policies.document_policy import DocumentPolicy
from app.modules.p2_gestion_documentos_preparacion.repositories import (
    presentation_material_repository as presentation_repository,
)
from app.modules.p2_gestion_documentos_preparacion.repositories.document_repository import (
    DocumentRepository,
)
from app.modules.p2_gestion_documentos_preparacion.services.document_retrieval_service import (
    DocumentContextUnavailableError,
    DocumentRetrievalService,
)

logger = logging.getLogger(__name__)

PRESENTATION_RETRIEVAL_INTENTS = (
    "contexto, antecedentes y planteamiento del problema",
    "objetivo general y objetivos especificos",
    "metodologia, muestra, procedimiento y decisiones metodologicas",
    "desarrollo, propuesta, arquitectura, componentes e implementacion",
    "resultados, validacion, pruebas, metricas y hallazgos",
    "conclusiones, recomendaciones, limitaciones y trabajo futuro",
)


class PresentationMaterialService:
    def __init__(
        self,
        *,
        db: Session,
        embeddings: EmbeddingProvider | None = None,
        vectors: VectorStoreProvider | None = None,
        generation_router: PresentationGenerationRouter | None = None,
    ) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.materials = presentation_repository.PresentationMaterialRepository(db)
        self.generation_router = generation_router
        self.retrieval: DocumentRetrievalService | None = None
        if embeddings is not None and vectors is not None:
            settings = get_settings()
            self.retrieval = DocumentRetrievalService(
                embeddings=embeddings,
                vectors=vectors,
                namespace_prefix=settings.pinecone_namespace_prefix,
                top_k=settings.question_retrieval_top_k,
                max_context_chars=settings.question_context_max_chars,
            )

    def generate(
        self,
        user: User,
        document_id: str,
        *,
        duration_minutes: int,
        regenerate: bool,
    ) -> PresentationMaterial:
        document = DocumentPolicy.can_read(user, self.documents.get_by_id(document_id))
        if document.status != DocumentStatus.PROCESSED:
            raise DocumentNotProcessedError
        if self.materials.get_ready_by_document(document.id) is not None and not regenerate:
            raise PresentationMaterialAlreadyExistsError
        if self.retrieval is None or self.generation_router is None:
            raise PresentationGenerationFailedError

        try:
            state = self.materials.start_generation(
                document=document, duration_minutes=duration_minutes
            )
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            logger.exception("Could not start presentation generation for %s", document.id)
            raise PresentationGenerationFailedError from None

        try:
            chunks = self.retrieval.retrieve(
                user_id=user.id,
                document_id=document.id,
                intents=PRESENTATION_RETRIEVAL_INTENTS,
            )
            result = self.generation_router.generate(
                PresentationGenerationRequest(
                    document_name=document.original_name,
                    duration_minutes=duration_minutes,
                    chunks=chunks,
                )
            )
        except PresentationGenerationFailed as exc:
            reason = f"{exc.primary_failure_reason};{exc.fallback_failure_reason}"
            self._mark_failed(state, reason=reason, latency_ms=exc.latency_ms)
            raise PresentationGenerationFailedError from None
        except (EmbeddingError, VectorStoreError, DocumentContextUnavailableError):
            logger.exception("Presentation retrieval failed for %s", document.id)
            self._mark_failed(state, reason="retrieval:unavailable", latency_ms=None)
            raise PresentationGenerationFailedError from None

        try:
            material = self.materials.get_by_document(document.id, for_update=True)
            if material is None:
                raise SQLAlchemyError("Presentation material disappeared during generation")
            self.materials.complete(material=material, result=result)
            self.db.commit()
            self.db.refresh(material)
            return material
        except SQLAlchemyError:
            self.db.rollback()
            logger.exception("Could not persist presentation material for %s", document.id)
            self._mark_failed(state, reason="persistence:failed", latency_ms=result.latency_ms)
            raise PresentationGenerationFailedError from None

    def get(self, user: User, document_id: str) -> PresentationMaterial:
        document = DocumentPolicy.can_read(user, self.documents.get_by_id(document_id))
        material = self.materials.get_ready_by_document(document.id)
        if material is None:
            raise PresentationMaterialNotFoundError
        return material

    def _mark_failed(
        self,
        state: presentation_repository.PresentationGenerationState,
        *,
        reason: str,
        latency_ms: int | None,
    ) -> None:
        self.db.rollback()
        material = self.materials.get_by_document(state.material.document_id, for_update=True)
        if material is None:
            logger.error("Presentation material disappeared while recording failure")
            return
        try:
            self.materials.mark_failed(
                material=material,
                had_ready_slides=state.had_ready_slides,
                reason=reason,
                latency_ms=latency_ms,
            )
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            logger.exception("Could not persist presentation generation failure")
