from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.p3_gestion_simulacion.models import Simulation


class SimulationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, simulation: Simulation) -> Simulation:
        self.db.add(simulation)
        self.db.flush()
        return simulation

    def get(self, simulation_id: str, *, for_update: bool = False) -> Simulation | None:
        statement = select(Simulation).where(Simulation.id == simulation_id)
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalars(statement).unique().one_or_none()

    def list_for_user(self, user_id: str) -> list[Simulation]:
        statement = (
            select(Simulation)
            .where(Simulation.user_id == user_id)
            .order_by(Simulation.created_at.desc(), Simulation.id.desc())
        )
        return list(self.db.scalars(statement).unique())

    def delete(self, simulation: Simulation) -> None:
        self.db.delete(simulation)
