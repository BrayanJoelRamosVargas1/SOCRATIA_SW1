from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import AdminUser
from app.modules.p6_gestion_administracion.schemas.dashboard import DashboardMetricsResponse
from app.modules.p6_gestion_administracion.services.dashboard_service import DashboardService

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]


@router.get("/language-audit")
def get_language_audit(admin_user: AdminUser, db: Database,
    group: Literal["questions", "jury_turns", "presentations", "slides", "feedback"] = "questions",
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    """Scan generated prose only, without inference APIs or exposing its contents."""
    from app.modules.p6_gestion_administracion.services.language_audit import audit_generated_language
    return audit_generated_language(db, group, offset, limit)


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
