from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.p4_gestion_evaluacion_resultados.models.evaluation import TurnClassification


class ScoreAvailability(BaseModel):
    content: bool
    communication: bool
    nonverbal: bool

class ReportQuestionDetail(BaseModel):
    question: str
    answer: str
    classification: TurnClassification | None
    turn_score: float | None
    strengths: list[str]
    weaknesses: list[str]
    missing_points: list[str]
    contradictions: list[str]
    evidence: list[str]
    time_taken_seconds: float | None = None
    filler_words_count: int | None = None
    eye_contact_score: float | None = None

    model_config = ConfigDict(from_attributes=True)

class SimulationReportResponse(BaseModel):
    simulation_id: str
    document_title: str
    date: datetime
    duration_minutes: float | None
    overall_score: float | None
    content_score: float | None
    communication_score: float | None
    nonverbal_score: float | None
    evaluation_version: str | None
    availability: ScoreAvailability
    questions: list[ReportQuestionDetail]

    model_config = ConfigDict(from_attributes=True)
