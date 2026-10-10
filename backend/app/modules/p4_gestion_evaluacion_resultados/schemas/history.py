from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.p3_gestion_simulacion.models.simulation import SimulationStatus
from app.modules.p4_gestion_evaluacion_resultados.models.evaluation import EvaluationStatus


class PerformanceHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    simulation_id: str
    document_title: str
    created_at: datetime
    duration_minutes: float
    simulation_status: SimulationStatus
    evaluation_status: EvaluationStatus | None
    overall_score: float | None
    content_score: float | None
    communication_score: float | None
    nonverbal_score: float | None
    delta_score: float | None
    report_url: str


class PerformanceHistorySummary(BaseModel):
    total_simulations: int
    evaluated_simulations: int
    latest_score: float | None
    best_score: float | None


class PerformanceHistoryResponse(BaseModel):
    summary: PerformanceHistorySummary
    items: list[PerformanceHistoryItem]
    total_items: int
    page: int
    page_size: int
    total_pages: int
