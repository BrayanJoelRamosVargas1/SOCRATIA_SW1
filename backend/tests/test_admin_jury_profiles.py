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


def test_admin_list_jury_profiles(admin_client):
    response = admin_client.get("/api/v1/admin/jury-profiles")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) >= 3
    assert "is_active" in data[0]


def test_student_cannot_access_admin_jury_profiles(client):
    register(client, "student-access@example.com")
    response = client.get("/api/v1/admin/jury-profiles")
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_admin_create_jury_profile(admin_client):
    payload = {
        "name": "Jurado Especial",
        "description": "Un jurado muy especial y diferente.",
        "focus_type": "METHODOLOGICAL",
        "strictness": 3,
        "interruption_level": "LOW",
        "is_active": True,
    }
    response = admin_client.post("/api/v1/admin/jury-profiles", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Jurado Especial"
    assert data["is_active"] is True


def test_admin_edit_jury_profile(admin_client):
    # First create
    payload = {
        "name": "Jurado Temporal",
        "description": "Jurado temporal para editar.",
        "focus_type": "TECHNICAL",
        "strictness": 2,
        "interruption_level": "MEDIUM",
        "is_active": True,
    }
    response = admin_client.post("/api/v1/admin/jury-profiles", json=payload)
    profile_id = response.json()["id"]

    # Edit
    edit_payload = {"strictness": 5, "name": "Jurado Editado"}
    response = admin_client.patch(f"/api/v1/admin/jury-profiles/{profile_id}", json=edit_payload)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["strictness"] == 5
    assert response.json()["name"] == "Jurado Editado"


from tests.test_simulation_configuration import register


def test_admin_deactivate_jury_profile_affects_student(admin_client, client):
    register(client, "student-list@example.com")
    # Get original list for student
    student_response = client.get("/api/v1/jury-profiles")
    assert student_response.status_code == status.HTTP_200_OK
    initial_student_count = len(student_response.json())

    # Admin creates profile
    payload = {
        "name": "Jurado a Desactivar",
        "description": "Este jurado será desactivado pronto.",
        "focus_type": "CRITICAL",
        "strictness": 4,
        "interruption_level": "HIGH",
        "is_active": True,
    }
    create_resp = admin_client.post("/api/v1/admin/jury-profiles", json=payload)
    profile_id = create_resp.json()["id"]

    # Student should see it
    student_resp2 = client.get("/api/v1/jury-profiles")
    assert len(student_resp2.json()) == initial_student_count + 1

    # Admin deactivates it
    admin_client.patch(f"/api/v1/admin/jury-profiles/{profile_id}", json={"is_active": False})

    # Student should NOT see it
    student_resp3 = client.get("/api/v1/jury-profiles")
    assert len(student_resp3.json()) == initial_student_count

    # Reactivate it
    admin_client.patch(f"/api/v1/admin/jury-profiles/{profile_id}", json={"is_active": True})

    # Student should see it again
    student_resp4 = client.get("/api/v1/jury-profiles")
    assert len(student_resp4.json()) == initial_student_count + 1


def test_student_cannot_modify_jury_profiles(client):
    register(client, "student-modify@example.com")
    response = client.post("/api/v1/admin/jury-profiles", json={})
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = client.patch("/api/v1/admin/jury-profiles/123", json={})
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = client.delete("/api/v1/admin/jury-profiles/123")
    assert response.status_code == status.HTTP_403_FORBIDDEN


from tests.test_simulation_configuration import create, ready_document


def test_admin_cannot_delete_used_profile(admin_client, client):
    # 1. Create a student to upload a document
    document_id = ready_document(client, "student-sim@example.com")

    # 2. Get the first default jury profile (it should be "Jurado Metodológico")
    response = admin_client.get("/api/v1/admin/jury-profiles")
    profiles = response.json()
    used_profile_id = profiles[0]["id"]

    # 3. Create a simulation
    create_response = create(client, document_id, used_profile_id)
    assert create_response.status_code == status.HTTP_201_CREATED

    # 4. Try to delete the used jury profile
    delete_resp = admin_client.delete(f"/api/v1/admin/jury-profiles/{used_profile_id}")
    assert delete_resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "associated simulations" in delete_resp.json()["detail"]


def test_admin_can_delete_unused_profile(admin_client):
    payload = {
        "name": "Jurado Para Borrar",
        "description": "Este jurado será borrado.",
        "focus_type": "CRITICAL",
        "strictness": 4,
        "interruption_level": "HIGH",
        "is_active": True,
    }
    create_resp = admin_client.post("/api/v1/admin/jury-profiles", json=payload)
    profile_id = create_resp.json()["id"]

    delete_resp = admin_client.delete(f"/api/v1/admin/jury-profiles/{profile_id}")
    assert delete_resp.status_code == status.HTTP_204_NO_CONTENT

    get_resp = admin_client.get(f"/api/v1/admin/jury-profiles/{profile_id}")
    assert get_resp.status_code == status.HTTP_404_NOT_FOUND
