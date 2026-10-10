from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.p1_gestion_identidad_seguridad.repositories.user_repository import UserRepository


def create_admin_and_login(client: TestClient, db_session: Session) -> dict:
    # Register an admin
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@test.com",
            "full_name": "Admin User",
            "password": "this_is_a_strong_password",
        },
    )

    # Make them admin in db
    repo = UserRepository(db_session)
    user = repo.get_by_email("admin@test.com")
    role = repo.get_or_create_role("Administrator")
    user.roles.append(role)
    db_session.commit()

    # Login
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "this_is_a_strong_password"},
    )
    token = resp.cookies.get("socratia_access")
    client.cookies.set("socratia_access", token)
    return {"token": token, "user": user}


def create_student_and_login(client: TestClient, db_session: Session) -> dict:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "student@test.com",
            "full_name": "Student User",
            "password": "this_is_a_strong_password",
        },
    )
    repo = UserRepository(db_session)
    user = repo.get_by_email("student@test.com")
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "student@test.com", "password": "this_is_a_strong_password"},
    )
    token = resp.cookies.get("socratia_access")
    client.cookies.set("socratia_access", token)
    return {"token": token, "user": user}


def test_admin_list_users(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)

    resp = client.get("/api/v1/admin/users")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 1


def test_admin_list_users_filters(client: TestClient, db_session: Session) -> None:
    create_admin_and_login(client, db_session)

    resp = client.get("/api/v1/admin/users?is_active=true&role=Administrator&search=Admin")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["email"] == "admin@test.com"


def test_student_cannot_access_admin_users(client: TestClient, db_session: Session) -> None:
    create_student_and_login(client, db_session)

    resp = client.get("/api/v1/admin/users")
    assert resp.status_code == 403


def test_unauthenticated_cannot_access_admin_users(client: TestClient) -> None:
    resp = client.get("/api/v1/admin/users")
    assert resp.status_code == 401


def test_admin_update_user_and_deactivate(client: TestClient, db_session: Session) -> None:
    admin_info = create_admin_and_login(client, db_session)
    # Register another user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "target@test.com",
            "full_name": "Target User",
            "password": "this_is_a_strong_password",
        },
    )
    repo = UserRepository(db_session)
    target_user = repo.get_by_email("target@test.com")
    target_id = target_user.id

    # Login as target to get their token
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "target@test.com", "password": "this_is_a_strong_password"},
    )
    target_token = resp.cookies.get("socratia_access")

    # Verify target can access profile
    client.cookies.set("socratia_access", target_token)
    resp = client.get("/api/v1/profile")
    assert resp.status_code == 200

    # As admin, deactivate target
    client.cookies.set("socratia_access", admin_info["token"])
    resp = client.patch(f"/api/v1/admin/users/{target_id}", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # Verify target is kicked out
    client.cookies.set("socratia_access", target_token)
    resp = client.get("/api/v1/profile")
    assert resp.status_code == 401

    # Admin reactivates
    client.cookies.set("socratia_access", admin_info["token"])
    resp = client.patch(f"/api/v1/admin/users/{target_id}", json={"is_active": True})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True

    # Target still cannot use old token because auth_version changed
    client.cookies.set("socratia_access", target_token)
    resp = client.get("/api/v1/profile")
    assert resp.status_code == 401


def test_admin_protect_last_active_admin(client: TestClient, db_session: Session) -> None:
    admin_info = create_admin_and_login(client, db_session)
    admin_id = admin_info["user"].id

    resp = client.patch(f"/api/v1/admin/users/{admin_id}", json={"is_active": False})
    assert resp.status_code == 400
    assert "last active administrator" in resp.json()["detail"]


def test_admin_payload_with_forbidden_fields_rejected(
    client: TestClient, db_session: Session
) -> None:
    admin_info = create_admin_and_login(client, db_session)
    admin_id = admin_info["user"].id

    resp = client.patch(
        f"/api/v1/admin/users/{admin_id}",
        json={
            "full_name": "New Name",
            "subscription": "Premium",  # not allowed
            "password_hash": "hacked",  # not allowed
        },
    )
    assert resp.status_code == 422
