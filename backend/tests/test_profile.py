from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_get_profile(client: TestClient) -> None:
    # 1. Register a user
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "profile@test.com",
            "full_name": "Profile Test",
            "password": "this_is_a_strong_password",
        },
    )
    assert resp.status_code == 201

    # 2. Login
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "profile@test.com", "password": "this_is_a_strong_password"},
    )
    assert resp.status_code == 200
    token = resp.cookies.get("socratia_access")
    assert token is not None

    # 3. Get profile
    client.cookies.set("socratia_access", token)
    resp = client.get("/api/v1/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "profile@test.com"
    assert data["full_name"] == "Profile Test"
    assert data["bio"] is None


def test_update_profile(client: TestClient, db_session: Session) -> None:
    # 1. Register a user
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "profile2@test.com",
            "full_name": "Profile Two",
            "password": "this_is_a_strong_password",
        },
    )
    assert resp.status_code == 201

    # 2. Login
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "profile2@test.com", "password": "this_is_a_strong_password"},
    )
    assert resp.status_code == 200
    token = resp.cookies.get("socratia_access")

    # 3. Update profile
    client.cookies.set("socratia_access", token)
    resp = client.patch(
        "/api/v1/profile", json={"full_name": "Updated Profile", "bio": "This is a new bio."}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Updated Profile"
    assert data["bio"] == "This is a new bio."
    assert "role" not in data or data["roles"] == []

    # 4. Check persistence
    resp = client.get("/api/v1/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == "Updated Profile"
    assert data["bio"] == "This is a new bio."

    # 5. Invalid data rejected (e.g. short name)
    resp = client.patch("/api/v1/profile", json={"full_name": "A"})
    assert resp.status_code == 422


def test_cannot_update_role_or_subscription(client: TestClient) -> None:
    # Register and login
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "profile3@test.com",
            "full_name": "Profile Three",
            "password": "this_is_a_strong_password",
        },
    )
    assert resp.status_code == 201
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "profile3@test.com", "password": "this_is_a_strong_password"},
    )
    token = resp.cookies.get("socratia_access")
    client.cookies.set("socratia_access", token)

    # Attempt to update role and subscription
    resp = client.patch(
        "/api/v1/profile",
        json={"role": "admin", "roles": ["admin"], "is_active": False, "subscription": "premium"},
    )
    # Since Pydantic will ignore extra fields (by default) or reject them, the request shouldn't change them.
    # It might return 200 but ignore the fields, or 422 if forbid_extra is set.
    # Let's verify they are ignored/rejected.
    resp = client.get("/api/v1/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_active"] is True
    assert "admin" not in data["roles"]


def test_unauthenticated_rejected(client: TestClient) -> None:
    resp = client.get("/api/v1/profile")
    assert resp.status_code == 401

    resp = client.patch("/api/v1/profile", json={"full_name": "Test"})
    assert resp.status_code == 401
