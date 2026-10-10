from collections.abc import Sequence

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import get_admin_user
from app.modules.p5_gestion_saas.schemas.subscription_schemas import (
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionUpdate,
)
from app.modules.p5_gestion_saas.services.subscription_service import SubscriptionService

router = APIRouter()


@router.get("/", response_model=list[SubscriptionResponse])
def get_subscriptions(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> Sequence[SubscriptionResponse]:
    return SubscriptionService.get_all_subscriptions(db)


@router.get("/{sub_id}", response_model=SubscriptionResponse)
def get_subscription(
    sub_id: str,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> SubscriptionResponse:
    return SubscriptionService.get_subscription(db, sub_id)


@router.post("/", response_model=SubscriptionResponse, status_code=201)
def create_subscription(
    data: SubscriptionCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> SubscriptionResponse:
    return SubscriptionService.create_subscription(db, data)


@router.patch("/{sub_id}", response_model=SubscriptionResponse)
def update_subscription(
    sub_id: str,
    data: SubscriptionUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> SubscriptionResponse:
    return SubscriptionService.update_subscription(db, sub_id, data)
