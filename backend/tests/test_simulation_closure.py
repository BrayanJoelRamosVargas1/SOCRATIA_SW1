import pytest
from datetime import datetime, timedelta, UTC
from uuid import uuid4

from app.modules.p3_gestion_simulacion.models import (
    Simulation,
    SimulationStatus,
    SimulationTurnState,
    SimulationQuestionSource,
)
from app.modules.p3_gestion_simulacion.services.session_service import SessionService
from app.modules.p3_gestion_simulacion.schemas.session import AnswerSubmitMessage, AnswerSubmitPayload


def test_closure_by_exhaustion(db_session, user, simulation, question_bank):
    # Ensure there's only 1 question to exhaust quickly
    sim = simulation(question_bank_id=question_bank.id, planned_duration_minutes=15)
    sim.status = SimulationStatus.ACTIVE
    sim.turn_state = SimulationTurnState.WAITING_STUDENT
    
    # We only have 1 question
    q = sim.questions[0]
    db_session.commit()

    svc = SessionService(db_session)
    # Answer the last question
    accepted, snapshot = svc.accept_answer(
        user,
        sim.id,
        "answer.submit",
        str(uuid4()),
        q.id,
        "Final answer",
        route_automatically=True
    )
    
    db_session.refresh(sim)
    assert sim.status == SimulationStatus.COMPLETED
    assert sim.turn_state is None
    assert sim.finished_at is not None
    assert snapshot.status == SimulationStatus.COMPLETED


def test_closure_by_time_limit(db_session, user, simulation, question_bank):
    sim = simulation(question_bank_id=question_bank.id, planned_duration_minutes=15)
    sim.status = SimulationStatus.ACTIVE
    sim.turn_state = SimulationTurnState.WAITING_STUDENT
    # 16 minutes ago
    sim.started_at = datetime.now(UTC) - timedelta(minutes=16)
    q = sim.questions[0]
    db_session.commit()

    svc = SessionService(db_session)
    
    # Time is up, so after answering this, it should close instead of asking the next
    # Even if there are more questions. Wait, let's test proceed_to_next_bank_question.
    sim.turn_state = SimulationTurnState.JURY_TURN
    db_session.commit()
    
    turn, snapshot = svc.proceed_to_next_bank_question(user, sim.id)
    
    db_session.refresh(sim)
    assert turn is None
    assert sim.status == SimulationStatus.COMPLETED
    assert snapshot.status == SimulationStatus.COMPLETED


def test_manual_closure_and_idempotence(db_session, user, simulation):
    sim = simulation(planned_duration_minutes=15)
    sim.status = SimulationStatus.ACTIVE
    sim.turn_state = SimulationTurnState.WAITING_STUDENT
    db_session.commit()

    svc = SessionService(db_session)
    
    # First close
    snapshot1 = svc.close_simulation(user, sim.id)
    db_session.refresh(sim)
    assert sim.status == SimulationStatus.COMPLETED
    assert sim.finished_at is not None

    # Second close (Idempotence)
    snapshot2 = svc.close_simulation(user, sim.id)
    assert snapshot1.finished_at == snapshot2.finished_at
    assert snapshot2.status == SimulationStatus.COMPLETED


def test_reconnection_completed(db_session, user, simulation):
    sim = simulation(planned_duration_minutes=15)
    sim.status = SimulationStatus.COMPLETED
    sim.finished_at = datetime.now(UTC)
    db_session.commit()

    # Reconnection just means fetching snapshot and checking state
    svc = SessionService(db_session)
    snapshot = svc.get_snapshot(user, sim.id)
    assert snapshot.status == SimulationStatus.COMPLETED
    assert snapshot.finished_at is not None
