from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.p4_gestion_evaluacion_resultados.models.evaluation import (
    EvaluationStatus,
    TurnClassification,
)


class TurnEvaluationResult(BaseModel):
    """Estructura estricta para la salida del LLM al evaluar un turno."""

    classification: TurnClassification = Field(
        description="Clasificación de la respuesta del usuario respecto a la pregunta y el contexto."
    )
    score: float = Field(
        description="Puntaje de 0 a 100 asignado al turno de acuerdo a la precisión y completitud."
    )
    strengths: list[str] = Field(description="Puntos fuertes de la respuesta del estudiante.")
    weaknesses: list[str] = Field(description="Puntos débiles o áreas de mejora.")
    missing_points: list[str] = Field(
        description="Puntos clave esperados que faltaron en la respuesta."
    )
    contradictions: list[str] = Field(
        description="Contradicciones de la respuesta respecto al material base."
    )
    evidence: list[str] = Field(
        description="Extractos textuales de la transcripción que respaldan la evaluación."
    )


class TurnEvaluationResponse(BaseModel):
    id: str
    simulation_turn_id: str
    source_question_id: str | None = None
    classification: TurnClassification | None = None
    turn_score: float | None = None
    strengths: list[str] = []
    weaknesses: list[str] = []
    missing_points: list[str] = []
    contradictions: list[str] = []
    evidence: list[str] = []
    time_taken_seconds: float | None = None
    filler_words_count: int | None = None
    eye_contact_score: float | None = None
    provider_used: str | None = None
    model_used: str | None = None
    evaluation_version: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EvaluationResponse(BaseModel):
    id: str
    simulation_id: str
    status: EvaluationStatus
    evaluation_version: str | None = None
    provider_used: str | None = None
    model_used: str | None = None
    content_score: float | None = None
    communication_score: float | None = Field(
        default=None, description="NOT_AVAILABLE if no audio features are present"
    )
    nonverbal_score: float | None = Field(
        default=None, description="NOT_AVAILABLE if no video features are present"
    )
    overall_score: float | None = None
    failure_reason: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    turn_evaluations: list[TurnEvaluationResponse] = []

    model_config = ConfigDict(from_attributes=True)
