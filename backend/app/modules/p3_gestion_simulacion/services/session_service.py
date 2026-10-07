import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p3_gestion_simulacion.exceptions import (
    InvalidTurnError,
    SimulationNotActiveError,
    SimulationNotReadyError,
)
from app.modules.p3_gestion_simulacion.models import (
    Simulation,
    SimulationQuestion,
    SimulationQuestionSource,
    SimulationQuestionStatus,
    SimulationStatus,
    SimulationTurn,
    SimulationTurnInputMode,
    SimulationTurnSpeaker,
    SimulationTurnState,
    SimulationTurnType,
)
from app.modules.p3_gestion_simulacion.policies.simulation_policy import (
    SimulationPolicy,
)
from app.modules.p3_gestion_simulacion.repositories.simulation_repository import (
    SimulationRepository,
)
from app.modules.p3_gestion_simulacion.repositories.turn_repository import (
    TurnRepository,
)
from app.modules.p3_gestion_simulacion.schemas.session import (
    AnswerAccepted,
    SessionQuestionResponse,
    SessionSnapshot,
    SessionTurnResponse,
)

logger = logging.getLogger(__name__)
EXPECTED_BANK_QUESTION_COUNT = 12


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class SessionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.simulations = SimulationRepository(db)
        self.turns = TurnRepository(db)

    def start(self, user: User, simulation_id: str) -> SessionSnapshot:
        simulation = SimulationPolicy.assert_owner(
            user, self.simulations.get(simulation_id, for_update=True)
        )
        if simulation.status == SimulationStatus.ACTIVE:
            if simulation.started_at is None or simulation.turn_state is None:
                raise SimulationNotActiveError
            logger.info("SIMULATION_START_REPLAY simulation_id=%s", simulation.id)
            snapshot = self._snapshot(simulation)
            self.db.commit()
            return snapshot
        if (
            simulation.status != SimulationStatus.READY
            or not simulation.camera_ready
            or not simulation.microphone_ready
            or not simulation.vision_ready
            or len(simulation.questions) != EXPECTED_BANK_QUESTION_COUNT
        ):
            raise SimulationNotReadyError

        first_question = self.turns.next_pending_question(simulation.id)
        if first_question is None:
            raise SimulationNotReadyError
        now = datetime.now(UTC)
        simulation.status = SimulationStatus.ACTIVE
        simulation.started_at = now
        simulation.turn_state = SimulationTurnState.JURY_TURN
        self._ask_question(simulation, first_question, now)
        simulation.turn_state = SimulationTurnState.WAITING_STUDENT
        self.db.commit()
        logger.info(
            "SIMULATION_STARTED simulation_id=%s question_id=%s",
            simulation.id,
            first_question.id,
        )
        snapshot = self._snapshot(simulation)
        self.db.commit()
        return snapshot

    def get_snapshot(self, user: User, simulation_id: str) -> SessionSnapshot:
        simulation = SimulationPolicy.assert_owner(user, self.simulations.get(simulation_id))
        
        if simulation.status == SimulationStatus.COMPLETED:
            # For a completed simulation, we just return the snapshot (no turn_state required)
            snapshot = self._snapshot(simulation)
            self.db.commit()
            return snapshot
            
        if (
            simulation.status != SimulationStatus.ACTIVE
            or simulation.started_at is None
            or simulation.turn_state is None
        ):
            raise SimulationNotActiveError
        snapshot = self._snapshot(simulation)
        self.db.commit()
        return snapshot

    def accept_answer(
        self,
        user: User,
        simulation_id: str,
        *,
        message_id: str,
        question_id: str,
        content: str,
        input_mode: SimulationTurnInputMode = SimulationTurnInputMode.TEXT,
        route_automatically: bool = True,
    ) -> tuple[AnswerAccepted, SessionSnapshot]:
        answer = content.strip()
        if not answer or len(answer) > 10_000:
            raise InvalidTurnError("La respuesta debe contener entre 1 y 10000 caracteres.")

        simulation = SimulationPolicy.assert_owner(
            user, self.simulations.get(simulation_id, for_update=True)
        )
        if simulation.status != SimulationStatus.ACTIVE:
            raise SimulationNotActiveError

        existing = self.turns.get_by_client_message(simulation.id, message_id)
        if existing is not None:
            logger.info(
                "ANSWER_REPLAYED simulation_id=%s sequence=%s",
                simulation.id,
                existing.sequence,
            )
            accepted = AnswerAccepted(
                message_id=message_id,
                answer_sequence=existing.sequence,
                duplicate=True,
            )
            snapshot = self._snapshot(simulation)
            self.db.commit()
            return accepted, snapshot

        current = self.turns.current_question(simulation.id)
        if simulation.turn_state != SimulationTurnState.WAITING_STUDENT or current is None:
            raise InvalidTurnError
        if current.id != question_id:
            raise InvalidTurnError("La pregunta enviada ya no es la pregunta actual.")

        now = datetime.now(UTC)
        simulation.turn_state = SimulationTurnState.PROCESSING
        answer_turn = self.turns.add(
            SimulationTurn(
                simulation_id=simulation.id,
                sequence=self.turns.next_sequence(simulation.id),
                speaker=SimulationTurnSpeaker.STUDENT,
                turn_type=SimulationTurnType.ANSWER,
                simulation_question_id=current.id,
                content=answer,
                input_mode=input_mode,
                client_message_id=message_id,
                started_at=now,
                completed_at=now,
            )
        )
        current.status = SimulationQuestionStatus.ANSWERED
        current.answered_at = now

        simulation.turn_state = SimulationTurnState.JURY_TURN

        # Check time limit
        time_exceeded = simulation.started_at and (now - simulation.started_at.replace(tzinfo=UTC)).total_seconds() >= simulation.planned_duration_minutes * 60

        if time_exceeded:
            self._close_simulation(simulation, now)
        elif route_automatically:
            next_question = self.turns.next_pending_question(simulation.id)
            if next_question is not None:
                self._ask_question(simulation, next_question, now)
                simulation.turn_state = SimulationTurnState.WAITING_STUDENT
            else:
                self._close_simulation(simulation, now)
        self.db.commit()
        logger.info(
            "ANSWER_ACCEPTED simulation_id=%s sequence=%s question_id=%s",
            simulation.id,
            answer_turn.sequence,
            current.id,
        )
        accepted = AnswerAccepted(
            message_id=message_id,
            answer_sequence=answer_turn.sequence,
            duplicate=False,
        )
        snapshot = self._snapshot(simulation)
        self.db.commit()
        return accepted, snapshot

    def _ask_question(
        self, simulation: Simulation, question: SimulationQuestion, now: datetime
    ) -> SimulationTurn:
        text = question.prompt_text or (question.question.question if question.question else "")
        if not text:
            raise SimulationNotReadyError
        turn = self.turns.add(
            SimulationTurn(
                simulation_id=simulation.id,
                sequence=self.turns.next_sequence(simulation.id),
                speaker=SimulationTurnSpeaker.JURY,
                turn_type=(
                    SimulationTurnType.QUESTION
                    if question.source.value == "BANK"
                    else SimulationTurnType.FOLLOW_UP
                ),
                simulation_question_id=question.id,
                question_source=question.source,
                content=text,
                started_at=now,
                completed_at=now,
            )
        )
        question.prompt_text = text
        question.status = SimulationQuestionStatus.ASKED
        question.asked_at = now
        return turn

    def add_follow_up_question(
        self,
        user: User,
        simulation_id: str,
        text: str,
        parent_question_id: str,
    ) -> tuple[SimulationTurn, SessionSnapshot]:
        simulation = SimulationPolicy.assert_owner(
            user, self.simulations.get(simulation_id, for_update=True)
        )
        if (
            simulation.status != SimulationStatus.ACTIVE
            or simulation.turn_state != SimulationTurnState.JURY_TURN
        ):
            raise InvalidTurnError

        parent = self.db.query(SimulationQuestion).filter_by(id=parent_question_id).first()
        if not parent:
            raise InvalidTurnError

        if parent.follow_up_depth >= 2:
            raise InvalidTurnError("Se ha alcanzado el límite máximo de preguntas de seguimiento.")

        now = datetime.now(UTC)
        time_exceeded = simulation.started_at and (now - simulation.started_at.replace(tzinfo=UTC)).total_seconds() >= simulation.planned_duration_minutes * 60
        if time_exceeded:
            self._close_simulation(simulation, now)
            self.db.commit()
            return None, self._snapshot(simulation)

        new_q = SimulationQuestion(
            simulation_id=simulation.id,
            position=parent.position,  # Follow up shares same position or we handle it otherwise. Actually position has unique constraint! We'll just assign position as max + 1? No, position is ordered. Let's just give it a high position temporarily, or better: position=max_position + 1
        )
        # We need a proper way to add follow ups.
        # Wait, since position is unique per simulation_id, we need to shift others or just use a float?
        # SimulationQuestion.position is Integer.
        # Let's shift remaining questions down by 1.
        self.db.query(SimulationQuestion).filter(
            SimulationQuestion.simulation_id == simulation.id,
            SimulationQuestion.position > parent.position,
        ).update({"position": SimulationQuestion.position + 1})

        new_q.position = parent.position + 1
        new_q.source = SimulationQuestionSource.FOLLOW_UP
        new_q.status = SimulationQuestionStatus.PENDING
        new_q.prompt_text = text
        new_q.parent_question_id = parent.id
        new_q.follow_up_depth = parent.follow_up_depth + 1

        self.db.add(new_q)
        self.db.flush()

        turn = self._ask_question(simulation, new_q, now)
        simulation.turn_state = SimulationTurnState.WAITING_STUDENT

        self.db.commit()
        snapshot = self._snapshot(simulation)
        return turn, snapshot

    def proceed_to_next_bank_question(
        self,
        user: User,
        simulation_id: str,
    ) -> tuple[SimulationTurn | None, SessionSnapshot]:
        simulation = SimulationPolicy.assert_owner(
            user, self.simulations.get(simulation_id, for_update=True)
        )
        if (
            simulation.status != SimulationStatus.ACTIVE
            or simulation.turn_state != SimulationTurnState.JURY_TURN
        ):
            raise InvalidTurnError

        now = datetime.now(UTC)
        time_exceeded = simulation.started_at and (now - simulation.started_at.replace(tzinfo=UTC)).total_seconds() >= simulation.planned_duration_minutes * 60

        next_question = self.turns.next_pending_question(simulation.id)
        turn = None
        if time_exceeded:
            self._close_simulation(simulation, now)
        elif next_question is not None:
            turn = self._ask_question(simulation, next_question, now)
            simulation.turn_state = SimulationTurnState.WAITING_STUDENT
        else:
            self._close_simulation(simulation, now)

        self.db.commit()
        snapshot = self._snapshot(simulation)
        return turn, snapshot

    
    def _close_simulation(self, simulation: Simulation, now: datetime) -> None:
        if simulation.status == SimulationStatus.COMPLETED:
            return
        simulation.status = SimulationStatus.COMPLETED
        simulation.turn_state = None
        simulation.finished_at = now

    def close_simulation(self, user: User, simulation_id: str) -> SessionSnapshot:
        simulation = SimulationPolicy.assert_owner(
            user, self.simulations.get(simulation_id, for_update=True)
        )
        if simulation.status == SimulationStatus.COMPLETED:
            return self._snapshot(simulation)
            
        if simulation.status != SimulationStatus.ACTIVE:
            raise InvalidTurnError("Simulation is not active")

        now = datetime.now(UTC)
        self._close_simulation(simulation, now)
        self.db.commit()
        return self._snapshot(simulation)

    def _snapshot(self, simulation: Simulation) -> SessionSnapshot:
        current = self.turns.current_question(simulation.id)
        transcript = self.turns.list_for_simulation(simulation.id)
        total = len(simulation.questions)
        answered = self.turns.answered_count(simulation.id)
        return SessionSnapshot(
            simulation_id=simulation.id,
            status=simulation.status,
            turn_state=simulation.turn_state,
            current_question=(
                SessionQuestionResponse(
                    id=current.id,
                    position=current.position + 1,
                    text=current.prompt_text
                    or (current.question.question if current.question else ""),
                    source=current.source,
                )
                if current is not None
                else None
            ),
            answered_questions=answered,
            total_questions=total,
            last_sequence=transcript[-1].sequence if transcript else 0,
            questions_exhausted=answered >= total and current is None,
            started_at=_utc(simulation.started_at),
            finished_at=_utc(simulation.finished_at) if simulation.finished_at else None,
            transcript=[
                SessionTurnResponse.model_validate(turn).model_copy(
                    update={"created_at": _utc(turn.created_at)}
                )
                for turn in transcript
            ],
        )
