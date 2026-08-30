from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.llm.presentation import WORDS_PER_MINUTE, PresentationGenerationResult
from app.modules.p2_gestion_documentos_preparacion.models.document import Document
from app.modules.p2_gestion_documentos_preparacion.models.presentation_material import (
    PresentationMaterial,
    PresentationMaterialStatus,
    PresentationSlide,
)


@dataclass(frozen=True, slots=True)
class PresentationGenerationState:
    material: PresentationMaterial
    had_ready_slides: bool


class PresentationMaterialRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_document(
        self, document_id: str, *, for_update: bool = False
    ) -> PresentationMaterial | None:
        statement = select(PresentationMaterial).where(
            PresentationMaterial.document_id == document_id
        )
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalars(statement).unique().one_or_none()

    def get_ready_by_document(self, document_id: str) -> PresentationMaterial | None:
        statement = select(PresentationMaterial).where(
            PresentationMaterial.document_id == document_id,
            PresentationMaterial.status == PresentationMaterialStatus.READY,
        )
        return self.db.scalars(statement).unique().one_or_none()

    def start_generation(
        self, *, document: Document, duration_minutes: int
    ) -> PresentationGenerationState:
        material = self.get_by_document(document.id, for_update=True)
        if material is None:
            material = PresentationMaterial(
                document_id=document.id,
                user_id=document.user_id,
                duration_minutes=duration_minutes,
                target_word_count=duration_minutes * WORDS_PER_MINUTE,
                status=PresentationMaterialStatus.GENERATING,
            )
            self.db.add(material)
            self.db.flush()
            return PresentationGenerationState(material=material, had_ready_slides=False)

        had_ready = material.status == PresentationMaterialStatus.READY and bool(material.slides)
        material.status = PresentationMaterialStatus.GENERATING
        material.duration_minutes = duration_minutes
        material.target_word_count = duration_minutes * WORDS_PER_MINUTE
        material.failure_reason = None
        self.db.flush()
        return PresentationGenerationState(material=material, had_ready_slides=had_ready)

    def complete(
        self, *, material: PresentationMaterial, result: PresentationGenerationResult
    ) -> None:
        material.slides.clear()
        self.db.flush()
        generated = result.presentation
        material.slides.extend(
            PresentationSlide(
                presentation_material=material,
                position=slide.position,
                title=slide.title,
                objective=slide.objective,
                bullet_points=slide.bullet_points,
                speaker_notes=slide.speaker_notes,
                estimated_seconds=slide.estimated_seconds,
                source_chunk_ids=slide.source_chunk_ids,
            )
            for slide in generated.slides
        )
        material.title = generated.title
        material.duration_minutes = generated.total_duration_minutes
        material.target_word_count = generated.target_word_count
        material.status = PresentationMaterialStatus.READY
        material.provider_used = result.provider
        material.model_used = result.model
        material.fallback_used = result.fallback_used
        material.latency_ms = result.latency_ms
        material.failure_reason = result.primary_failure_reason
        self.db.flush()

    def mark_failed(
        self,
        *,
        material: PresentationMaterial,
        had_ready_slides: bool,
        reason: str,
        latency_ms: int | None,
    ) -> None:
        material.status = (
            PresentationMaterialStatus.READY
            if had_ready_slides
            else PresentationMaterialStatus.FAILED
        )
        material.failure_reason = reason[:300]
        material.latency_ms = latency_ms
        self.db.flush()
