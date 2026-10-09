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
