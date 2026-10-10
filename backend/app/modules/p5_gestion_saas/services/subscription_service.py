from collections.abc import Sequence
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p5_gestion_saas.models.plan import Plan
from app.modules.p5_gestion_saas.models.subscription import Subscription, SubscriptionStatus
from app.modules.p5_gestion_saas.schemas.subscription_schemas import (
    SubscriptionCreate,
    SubscriptionUpdate,
)


class SubscriptionService:
    @staticmethod
    def get_all_subscriptions(db: Session) -> Sequence[Subscription]:
        result = db.execute(select(Subscription))
        return result.scalars().all()

    @staticmethod
    def get_subscription(db: Session, sub_id: str) -> Subscription:
        sub = db.get(Subscription, sub_id)
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found"
            )
        return sub

    @staticmethod
    def _check_user_active_subs(db: Session, user_id: str):
        # Transactional invariant: max 1 active sub per user
        active_subs = db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
        if active_subs.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has an active subscription. Cannot have 2 active subscriptions.",
            )

    @staticmethod
    def create_subscription(db: Session, data: SubscriptionCreate) -> Subscription:
        # Check user exists
        user = db.get(User, data.user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Check plan exists and active
        plan = db.get(Plan, data.plan_id)
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        if not plan.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Plan is inactive and cannot be assigned",
            )

        # Enforce invariant
        SubscriptionService._check_user_active_subs(db, data.user_id)

        new_sub = Subscription(
            user_id=data.user_id,
            plan_id=data.plan_id,
            status=SubscriptionStatus.ACTIVE,
            price_at_subscription=plan.price,
        )
        db.add(new_sub)
        db.commit()
        db.refresh(new_sub)
        return new_sub

    @staticmethod
    def update_subscription(db: Session, sub_id: str, data: SubscriptionUpdate) -> Subscription:
        sub = SubscriptionService.get_subscription(db, sub_id)

        if data.status:
            # If changing to active, we must check if another active sub exists
            if data.status == SubscriptionStatus.ACTIVE and sub.status != SubscriptionStatus.ACTIVE:
                SubscriptionService._check_user_active_subs(db, sub.user_id)

            # If cancelling, record cancelled_at
            if (
                data.status == SubscriptionStatus.CANCELLED
                and sub.status != SubscriptionStatus.CANCELLED
            ):
                sub.cancelled_at = datetime.now(UTC)

            sub.status = data.status

        if data.plan_id:
            if sub.status == SubscriptionStatus.ACTIVE and data.plan_id != sub.plan_id:
                # Need to update plan
                plan = db.get(Plan, data.plan_id)
                if not plan:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
                    )
                if not plan.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Plan is inactive and cannot be assigned",
                    )
                sub.plan_id = plan.id
                sub.price_at_subscription = plan.price

        db.commit()
        db.refresh(sub)
        return sub
