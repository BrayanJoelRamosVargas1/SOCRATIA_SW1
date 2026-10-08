from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import get_current_user
from app.modules.p4_gestion_evaluacion_resultados.schemas.history import PerformanceHistoryResponse
from app.modules.p4_gestion_evaluacion_resultados.services.history_service import HistoryService

router = APIRouter()

@router.get("/performance-history", response_model=PerformanceHistoryResponse)
def get_performance_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    document_id: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = HistoryService(db)
    return service.get_history_for_user(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        document_id=document_id,
        status=status
    )
