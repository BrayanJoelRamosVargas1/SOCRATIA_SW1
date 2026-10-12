from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import get_current_user
from app.modules.p5_gestion_saas.models.plan import Plan
from app.modules.p5_gestion_saas.schemas.plan_schemas import PlanResponse
from app.modules.p5_gestion_saas.schemas.subscription_schemas import (
    StudentCurrentSubscriptionResponse,
    StudentSubscriptionChange,
    StudentSubscriptionCreate,
    SubscriptionResponse,
)
from app.modules.p5_gestion_saas.services.subscription_service import SubscriptionService

router = APIRouter()


@router.get("/", response_model=StudentCurrentSubscriptionResponse)
def get_my_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentCurrentSubscriptionResponse:
    active_sub = SubscriptionService.get_user_active_subscription(db, current_user.id)
    plan_resp = None
    if active_sub:
        plan = db.get(Plan, active_sub.plan_id)
        if plan:
            plan_resp = PlanResponse.model_validate(plan)

    all_subs = SubscriptionService.get_user_subscriptions(db, current_user.id)
    history_resp = [SubscriptionResponse.model_validate(s) for s in all_subs]

    return StudentCurrentSubscriptionResponse(
        subscription=SubscriptionResponse.model_validate(active_sub) if active_sub else None,
        plan=plan_resp,
        history=history_resp,
    )


@router.post("/", response_model=SubscriptionResponse, status_code=201)
def subscribe(
    data: StudentSubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    sub = SubscriptionService.subscribe_student(db, current_user.id, data.plan_id)
    return SubscriptionResponse.model_validate(sub)


@router.patch("/", response_model=SubscriptionResponse)
def change_plan(
    data: StudentSubscriptionChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    sub = SubscriptionService.change_student_plan(db, current_user.id, data.plan_id)
    return SubscriptionResponse.model_validate(sub)


@router.post("/cancel", response_model=SubscriptionResponse)
def cancel_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionResponse:
    sub = SubscriptionService.cancel_student_subscription(db, current_user.id)
    return SubscriptionResponse.model_validate(sub)
