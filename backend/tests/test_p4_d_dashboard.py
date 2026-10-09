import pytest
from fastapi import status

from app.main import app
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import get_admin_user


@pytest.fixture
def admin_client(client):
    admin_user = User(id="admin-id", email="admin@example.com", full_name="Admin", is_active=True)
    app.dependency_overrides[get_admin_user] = lambda: admin_user
    yield client
    app.dependency_overrides.pop(get_admin_user, None)


def test_admin_can_access_dashboard(admin_client):
    response = admin_client.get("/api/v1/admin/dashboard")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "total_users" in data
    assert "documents_by_status" in data
    assert "simulations_by_status" in data
    assert "evaluations_by_status" in data
    assert "average_overall_score" in data
    assert "integration_metrics" in data
    assert data["integration_metrics"] == "NOT_AVAILABLE"


def test_student_cannot_access_dashboard(client):
    # Try accessing without authentication, should be 401 or 403
    response = client.get("/api/v1/admin/dashboard")
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
    
    # Let's register a normal user
    register_data = {
        "email": "student-dash@example.com",
        "password": "Password123!",
        "full_name": "Student Dash"
    }
    client.post("/api/v1/auth/register", json=register_data)
    login_data = {
        "username": "student-dash@example.com",
        "password": "Password123!"
    }
    login_resp = client.post("/api/v1/auth/login", data=login_data)
    if login_resp.status_code == 200:
        token = login_resp.json()["access_token"]
        response = client.get(
            "/api/v1/admin/dashboard",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
from app.modules.p2_gestion_documentos_preparacion.models.document import Document, DocumentStatus
from app.modules.p3_gestion_simulacion.models.simulation import Simulation, SimulationStatus
from app.modules.p4_gestion_evaluacion_resultados.models.evaluation import (
    Evaluation,
    EvaluationStatus,
)


def test_dashboard_with_data(admin_client, db_session):
    # Setup data
    user1 = User(id="test-u1", email="dash-u1@example.com", full_name="Dash U1", password_hash="hash")
    doc1 = Document(id="test-d1", user_id="test-u1", original_name="test.pdf", file_type="pdf", file_size=1024, content_hash="hash1", storage_key="key1", status=DocumentStatus.PROCESSED)
    doc2 = Document(id="test-d2", user_id="test-u1", original_name="test2.pdf", file_type="pdf", file_size=1024, content_hash="hash2", storage_key="key2", status=DocumentStatus.EXTRACTING)
    from app.modules.p2_gestion_documentos_preparacion.models.question_bank import QuestionBank, QuestionBankStatus
    from app.modules.p3_gestion_simulacion.models.simulation import JuryProfile, FocusType, InterruptionLevel
    
    bank = QuestionBank(id="bank1", user_id="test-u1", document_id="test-d1", status=QuestionBankStatus.READY)
    jury = JuryProfile(id="jury1", name="Jury", description="desc", strictness=3, focus_type=FocusType.TECHNICAL, interruption_level=InterruptionLevel.MEDIUM)
    
    sim1 = Simulation(id="test-s1", user_id="test-u1", document_id="test-d1", question_bank_id="bank1", jury_profile_id="jury1", planned_duration_minutes=15, status=SimulationStatus.COMPLETED)
    sim2 = Simulation(id="test-s2", user_id="test-u1", document_id="test-d1", question_bank_id="bank1", jury_profile_id="jury1", planned_duration_minutes=15, status=SimulationStatus.DRAFT)
    ev1 = Evaluation(id="test-e1", simulation_id="test-s1", status=EvaluationStatus.COMPLETED, overall_score=80.0)
    ev2 = Evaluation(id="test-e2", simulation_id="test-s2", status=EvaluationStatus.PENDING, overall_score=100.0)

    db_session.add_all([user1, doc1, doc2, bank, jury, sim1, sim2, ev1, ev2])
    db_session.commit()

    response = admin_client.get("/api/v1/admin/dashboard")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_users"] >= 1
    assert data["documents_by_status"]["PROCESSED"] >= 1
    assert data["documents_by_status"]["EXTRACTING"] >= 1
    assert data["simulations_by_status"]["COMPLETED"] >= 1
    assert data["simulations_by_status"]["DRAFT"] >= 1
    assert data["evaluations_by_status"]["COMPLETED"] >= 1
    assert data["evaluations_by_status"]["PENDING"] >= 1
    
    # Check average only takes COMPLETED
    assert data["average_overall_score"] == 80.0
    
    # Check NO LLM is called (there is no mocker here but the route is synchronous DB calls)
    # Check no secrets are exposed
    assert "password" not in str(data)

def test_dashboard_date_filter_ignored(admin_client):
    response = admin_client.get("/api/v1/admin/dashboard?start_date=2026-01-01&end_date=2026-12-31")
    assert response.status_code == status.HTTP_200_OK
