from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.models.question_bank import (
    Question,
    QuestionBank,
)
from app.modules.p3_gestion_simulacion.models import (
    Simulation,
    SimulationQuestion,
    SimulationQuestionSource,
    SimulationQuestionStatus,
    SimulationStatus,
    SimulationTurnState,
)
from app.modules.p3_gestion_simulacion.services.session_service import SessionService


@pytest.fixture
def user(db_session):
    u = User(id=str(uuid4()), email="test@test.com", password_hash="hash", full_name="Test User")
    db_session.add(u)
    db_session.commit()
    return u

@pytest.fixture
def question_bank(db_session, user):
    from app.modules.p2_gestion_documentos_preparacion.models.document import Document
    from app.modules.p2_gestion_documentos_preparacion.models.question_bank import (
        QuestionCategory,
        QuestionDifficulty,
    )
    
    doc = Document(
        id=str(uuid4()), 
        user_id=user.id, 
        original_name="Test Doc", 
        file_type="pdf",
        file_size=100,
        content_hash="hash",
        storage_key="key"
    )
    db_session.add(doc)
    db_session.commit()
    
    qb = QuestionBank(id=str(uuid4()), user_id=user.id, document_id=doc.id)
    q = Question(
        id=str(uuid4()), 
        question_bank_id=qb.id, 
        question="Q1", 
        expected_answer_points=[], 
        category=QuestionCategory.CONCEPTUAL,
        difficulty=QuestionDifficulty.MEDIUM,
        source_chunk_ids=[],
        position=0
    )
    db_session.add(qb)
    db_session.add(q)
    db_session.commit()
    return qb

@pytest.fixture
def simulation(db_session, user, question_bank):
    def _simulation(**kwargs):
        from app.modules.p3_gestion_simulacion.models.simulation import JuryProfile, FocusType, InterruptionLevel
        jp = JuryProfile(
            id=str(uuid4()), 
            name=f"Jury {uuid4()}", 
            description="desc",
            focus_type=FocusType.TECHNICAL,
            strictness=3,
            interruption_level=InterruptionLevel.MEDIUM
        )
        db_session.add(jp)
        db_session.flush()

        sim = Simulation(
            id=str(uuid4()),
            user_id=user.id,
            document_id=question_bank.document_id,
            jury_profile_id=jp.id,
            question_bank_id=kwargs.pop("question_bank_id", question_bank.id),
            **kwargs
        )
        sim_q = SimulationQuestion(
            id=str(uuid4()),
            simulation_id=sim.id,
            question_id=question_bank.questions[0].id,
            source=SimulationQuestionSource.BANK,
            position=0,
            status=SimulationQuestionStatus.PENDING
        )
        db_session.add(sim)
        db_session.add(sim_q)
        db_session.commit()
        return sim
    return _simulation


def test_closure_by_exhaustion(db_session, user, simulation, question_bank):
    # Ensure there's only 1 question to exhaust quickly
    sim = simulation(question_bank_id=question_bank.id, planned_duration_minutes=15)
    sim.status = SimulationStatus.ACTIVE
    sim.started_at = datetime.now(UTC)
    sim.turn_state = SimulationTurnState.WAITING_STUDENT
    
    # We only have 1 question
    q = sim.questions[0]
    q.status = SimulationQuestionStatus.ASKED
    db_session.commit()

    svc = SessionService(db_session)
    # Answer the last question
    accepted, snapshot = svc.accept_answer(
        user,
        sim.id,
        message_id=str(uuid4()),
        question_id=q.id,
        content="Final answer",
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
    sim.started_at = datetime.now(UTC)
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
    sim.started_at = datetime.now(UTC) - timedelta(minutes=10)
    sim.finished_at = datetime.now(UTC)
    db_session.commit()

    # Reconnection just means fetching snapshot and checking state
    svc = SessionService(db_session)
    snapshot = svc.get_snapshot(user, sim.id)
    assert snapshot.status == SimulationStatus.COMPLETED
    assert snapshot.finished_at is not None
