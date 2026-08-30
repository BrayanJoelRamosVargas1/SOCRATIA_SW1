from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.p2_gestion_documentos_preparacion.models.presentation_material import (
    PresentationMaterialStatus,
)


class PresentationGenerationInput(BaseModel):
    duration_minutes: int = Field(ge=5, le=30)


class PresentationSlideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    position: int
    title: str
    objective: str
    bullet_points: list[str]
    speaker_notes: str
    estimated_seconds: int


class PresentationMaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    title: str
    duration_minutes: int
    target_word_count: int
    status: PresentationMaterialStatus
    provider_used: str
    model_used: str
    fallback_used: bool
    latency_ms: int | None
    created_at: datetime
    updated_at: datetime
    slides: list[PresentationSlideResponse]
