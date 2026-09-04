from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.p3_gestion_simulacion.models import (
    SimulationQuestion,
    SimulationQuestionStatus,
    SimulationTurn,
)


class TurnRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, turn: SimulationTurn) -> SimulationTurn:
        self.db.add(turn)
        self.db.flush()
        return turn

    def next_sequence(self, simulation_id: str) -> int:
        last = self.db.scalar(
            select(func.max(SimulationTurn.sequence)).where(
                SimulationTurn.simulation_id == simulation_id
            )
        )
        return int(last or 0) + 1

    def get_by_client_message(
        self, simulation_id: str, client_message_id: str
    ) -> SimulationTurn | None:
        return self.db.scalar(
            select(SimulationTurn).where(
                SimulationTurn.simulation_id == simulation_id,
                SimulationTurn.client_message_id == client_message_id,
            )
        )

    def list_for_simulation(self, simulation_id: str) -> list[SimulationTurn]:
        return list(
            self.db.scalars(
                select(SimulationTurn)
                .where(SimulationTurn.simulation_id == simulation_id)
                .order_by(SimulationTurn.sequence)
            ).unique()
        )

    def current_question(self, simulation_id: str) -> SimulationQuestion | None:
        return self.db.scalar(
            select(SimulationQuestion)
            .where(
                SimulationQuestion.simulation_id == simulation_id,
                SimulationQuestion.status == SimulationQuestionStatus.ASKED,
            )
            .order_by(SimulationQuestion.position)
        )

    def next_pending_question(self, simulation_id: str) -> SimulationQuestion | None:
        return self.db.scalar(
            select(SimulationQuestion)
            .where(
                SimulationQuestion.simulation_id == simulation_id,
                SimulationQuestion.status == SimulationQuestionStatus.PENDING,
            )
            .order_by(SimulationQuestion.position)
            .limit(1)
        )

    def answered_count(self, simulation_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(SimulationQuestion)
                .where(
                    SimulationQuestion.simulation_id == simulation_id,
                    SimulationQuestion.status == SimulationQuestionStatus.ANSWERED,
                )
            )
            or 0
        )
