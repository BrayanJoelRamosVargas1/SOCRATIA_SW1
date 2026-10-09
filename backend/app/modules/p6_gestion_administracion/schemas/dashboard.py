from typing import Any

from pydantic import BaseModel


class DashboardMetricsResponse(BaseModel):
    total_users: int
    documents_by_status: dict[str, int]
    simulations_by_status: dict[str, int]
    evaluations_by_status: dict[str, int]
    average_overall_score: float | None
    integration_metrics: Any
