from collections.abc import Sequence
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.p5_gestion_saas.models.plan import Plan
from app.modules.p5_gestion_saas.schemas.plan_schemas import PlanCreate, PlanUpdate

DEFAULT_ACADEMIC_PLANS = [
    {
        "name": "Plan Estudiante Gratuito",
        "description": "Acceso esencial para preparar tu primera defensa académica con jurado estándar.",
        "price": Decimal("0.00"),
        "max_documents": 2,
        "max_simulations": 3,
        "max_storage_mb": 25,
        "is_active": True,
    },
    {
        "name": "Plan Investigador Pro",
        "description": "Acceso completo a jurados socráticos avanzados, HUD biomecánico en vivo y reportes ejecutivos.",
        "price": Decimal("19.99"),
        "max_documents": 10,
        "max_simulations": 30,
        "max_storage_mb": 150,
        "is_active": True,
    },
    {
        "name": "Plan Excelencia Doctoral",
        "description": "Máxima rigurosidad académica para maestrías y doctorados, seguimiento longitudinal y exportación.",
        "price": Decimal("49.99"),
        "max_documents": 50,
        "max_simulations": 100,
        "max_storage_mb": 500,
        "is_active": True,
    },
]


class PlanService:
    @staticmethod
    def ensure_default_plans(db: Session) -> None:
        """Seed default academic plans if fewer than 2 active plans exist in the system."""
        existing_count = db.execute(select(Plan).where(Plan.is_active.is_(True))).scalars().all()
        if len(existing_count) < 2:
            for plan_data in DEFAULT_ACADEMIC_PLANS:
                existing = db.execute(select(Plan).where(Plan.name == plan_data["name"])).scalars().first()
                if not existing:
                    db.add(Plan(**plan_data))
            db.commit()

    @staticmethod
    def get_all_plans(db: Session) -> Sequence[Plan]:
        PlanService.ensure_default_plans(db)
        result = db.execute(select(Plan))
        return result.scalars().all()

    @staticmethod
    def get_active_plans(db: Session) -> Sequence[Plan]:
        PlanService.ensure_default_plans(db)
        result = db.execute(select(Plan).where(Plan.is_active.is_(True)))
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
