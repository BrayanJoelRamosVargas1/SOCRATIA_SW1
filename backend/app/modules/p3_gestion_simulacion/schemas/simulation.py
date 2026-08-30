from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.p3_gestion_simulacion.models import (
    FocusType,
    InterruptionLevel,
    SimulationStatus,
)


class JuryProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    focus_type: FocusType
    strictness: int
    interruption_level: InterruptionLevel


class SimulationDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str = Field(validation_alias="original_name")


class SimulationCreateInput(BaseModel):
    document_id: str
    jury_profile_id: str
    planned_duration_minutes: int = Field(ge=5, le=30)


class CalibrationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    camera_ready: bool
    microphone_ready: bool
    vision_ready: bool


class SimulationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: SimulationStatus
    planned_duration_minutes: int
    camera_ready: bool
    microphone_ready: bool
    vision_ready: bool
    question_count: int
    document: SimulationDocumentResponse
    jury_profile: JuryProfileResponse
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime
