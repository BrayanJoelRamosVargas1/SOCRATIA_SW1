from collections.abc import Sequence

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import get_current_user
from app.modules.p5_gestion_saas.schemas.plan_schemas import PlanResponse
from app.modules.p5_gestion_saas.services.plan_service import PlanService

router = APIRouter()


@router.get("/", response_model=list[PlanResponse])
def get_public_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Sequence[PlanResponse]:
    return PlanService.get_active_plans(db)
