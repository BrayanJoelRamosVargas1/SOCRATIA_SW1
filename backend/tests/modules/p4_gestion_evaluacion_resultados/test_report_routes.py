import pytest
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid

from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p3_gestion_simulacion.models.simulation import Simulation, SimulationStatus

@pytest.fixture
def test_user(db_session: Session) -> User:
    user = User(email="test@test.com", password_hash="hash", full_name="Test User")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def other_user(db_session: Session) -> User:
    user = User(email="other@test.com", password_hash="hash", full_name="Other User")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

def test_report_unauthorized(client: TestClient):
    response = client.get("/api/v1/simulations/123/report")
    assert response.status_code == 401

def test_report_forbidden_other_user(client: TestClient, db_session: Session, test_user: User, other_user: User):
    from app.modules.p1_gestion_identidad_seguridad.policies.current_user import get_current_user
    app.dependency_overrides[get_current_user] = lambda: test_user
    
    from app.modules.p2_gestion_documentos_preparacion.models.document import Document
    from app.modules.p2_gestion_documentos_preparacion.models.question_bank import QuestionBank
    from app.modules.p3_gestion_simulacion.models.simulation import JuryProfile

    doc = Document(user_id=other_user.id, original_name="x", file_type="pdf", file_size=1, content_hash="x1", storage_key="x1", status="PROCESSED")
    db_session.add(doc)
    db_session.commit()
    
    qb = QuestionBank(document_id=doc.id, user_id=doc.user_id, status="READY")
    db_session.add(qb)
    db_session.commit()
    
    jp = JuryProfile(id="dummy1", name="Dummy1", description="dummy", focus_type="TECHNICAL", strictness=1, interruption_level="LOW")
    db_session.add(jp)
    try:
        db_session.commit()
    except Exception:
        db_session.rollback()

    sim = Simulation(
        user_id=other_user.id,
        document_id=doc.id,
        question_bank_id=qb.id,
        jury_profile_id="dummy1",
        status=SimulationStatus.COMPLETED,
        planned_duration_minutes=15
    )
    db_session.add(sim)
    db_session.commit()
    
    response = client.get(f"/api/v1/simulations/{sim.id}/report")
    assert response.status_code == 403
    app.dependency_overrides.clear()

def test_report_not_completed_sim(client: TestClient, db_session: Session, test_user: User):
    from app.modules.p1_gestion_identidad_seguridad.policies.current_user import get_current_user
    app.dependency_overrides[get_current_user] = lambda: test_user

    from app.modules.p2_gestion_documentos_preparacion.models.document import Document
    from app.modules.p2_gestion_documentos_preparacion.models.question_bank import QuestionBank
    from app.modules.p3_gestion_simulacion.models.simulation import JuryProfile

    doc = Document(user_id=test_user.id, original_name="x", file_type="pdf", file_size=1, content_hash="x2", storage_key="x2", status="PROCESSED")
    db_session.add(doc)
    db_session.commit()
    
    qb = QuestionBank(document_id=doc.id, user_id=doc.user_id, status="READY")
    db_session.add(qb)
    db_session.commit()
    
    jp = JuryProfile(id="dummy2", name="Dummy2", description="dummy", focus_type="TECHNICAL", strictness=1, interruption_level="LOW")
    db_session.add(jp)
    try:
        db_session.commit()
    except Exception:
        db_session.rollback()

    sim = Simulation(
        user_id=test_user.id,
        document_id=doc.id,
        question_bank_id=qb.id,
        jury_profile_id="dummy2",
        status=SimulationStatus.ACTIVE,
        planned_duration_minutes=15
    )
    db_session.add(sim)
    db_session.commit()

    response = client.get(f"/api/v1/simulations/{sim.id}/report")
    assert response.status_code == 400
    assert "not completed" in response.json()["detail"]
    app.dependency_overrides.clear()
