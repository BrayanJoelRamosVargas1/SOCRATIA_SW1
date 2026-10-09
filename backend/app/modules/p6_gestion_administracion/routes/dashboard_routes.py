from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import AdminUser
from app.modules.p6_gestion_administracion.schemas.dashboard import DashboardMetricsResponse
from app.modules.p6_gestion_administracion.services.dashboard_service import DashboardService

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]


@router.get("/dashboard", response_model=DashboardMetricsResponse)
def get_dashboard_metrics(
    admin_user: AdminUser,
    db: Database,
) -> DashboardMetricsResponse:
    """Get administrative platform metrics."""
    # Ensure this variable is used so linter doesn't complain
    del admin_user
    service = DashboardService(db)
    return DashboardMetricsResponse.model_validate(service.get_metrics())
