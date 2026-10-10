from collections.abc import Sequence

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import get_admin_user
from app.modules.p5_gestion_saas.schemas.plan_schemas import (
    PlanCreate,
    PlanResponse,
    PlanUpdate,
)
from app.modules.p5_gestion_saas.services.plan_service import PlanService

router = APIRouter()


@router.get("/", response_model=list[PlanResponse])
def get_plans(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> Sequence[PlanResponse]:
    return PlanService.get_all_plans(db)


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> PlanResponse:
    return PlanService.get_plan(db, plan_id)


@router.post("/", response_model=PlanResponse, status_code=201)
def create_plan(
    data: PlanCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> PlanResponse:
    return PlanService.create_plan(db, data)


@router.patch("/{plan_id}", response_model=PlanResponse)
def update_plan(
    plan_id: str,
    data: PlanUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> PlanResponse:
    return PlanService.update_plan(db, plan_id, data)
