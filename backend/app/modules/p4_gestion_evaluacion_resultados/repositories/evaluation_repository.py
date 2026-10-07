from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.p4_gestion_evaluacion_resultados.models.evaluation import Evaluation


class EvaluationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_simulation_id(self, simulation_id: str) -> Evaluation | None:
        stmt = select(Evaluation).where(Evaluation.simulation_id == simulation_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, evaluation: Evaluation) -> Evaluation:
        self.db.add(evaluation)
        self.db.flush()
        return evaluation

    def update(self, evaluation: Evaluation) -> Evaluation:
        self.db.add(evaluation)
        self.db.flush()
        return evaluation
