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


class AdminJuryProfileResponse(JuryProfileResponse):
    is_active: bool
    created_at: datetime
    updated_at: datetime


class JuryProfileCreateInput(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=10, max_length=500)
    focus_type: FocusType
    strictness: int = Field(ge=1, le=5)
    interruption_level: InterruptionLevel
    is_active: bool = True


class JuryProfileUpdateInput(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=100)
    description: str | None = Field(default=None, min_length=10, max_length=500)
    focus_type: FocusType | None = None
    strictness: int | None = Field(default=None, ge=1, le=5)
    interruption_level: InterruptionLevel | None = None
    is_active: bool | None = None


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
