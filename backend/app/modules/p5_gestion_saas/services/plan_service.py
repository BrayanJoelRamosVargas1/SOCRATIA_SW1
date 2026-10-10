from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.p5_gestion_saas.models.plan import Plan
from app.modules.p5_gestion_saas.schemas.plan_schemas import PlanCreate, PlanUpdate


class PlanService:
    @staticmethod
    def get_all_plans(db: Session) -> Sequence[Plan]:
        result = db.execute(select(Plan))
        return result.scalars().all()

    @staticmethod
    def get_plan(db: Session, plan_id: str) -> Plan:
        plan = db.get(Plan, plan_id)
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        return plan

    @staticmethod
    def create_plan(db: Session, data: PlanCreate) -> Plan:
        # Check if name is taken
        existing = db.execute(select(Plan).where(Plan.name == data.name))
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Plan name already exists"
            )

        new_plan = Plan(**data.model_dump())
        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)
        return new_plan

    @staticmethod
    def update_plan(db: Session, plan_id: str, data: PlanUpdate) -> Plan:
        plan = PlanService.get_plan(db, plan_id)

        if data.name is not None and data.name != plan.name:
            existing = db.execute(select(Plan).where(Plan.name == data.name))
            if existing.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Plan name already exists"
                )

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(plan, key, value)

        db.commit()
        db.refresh(plan)
        return plan
