from fastapi.testclient import TestClient


def test_complete_authentication_flow(client: TestClient) -> None:
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "Ada@Example.com",
            "full_name": "Ada Lovelace",
            "password": "analytical-engine",
        },
    )
    assert registration.status_code == 201
    assert registration.json()["user"]["email"] == "ada@example.com"
    assert registration.json()["user"]["roles"] == ["student"]
    assert "socratia_access" in registration.cookies
    assert "socratia_refresh" in registration.cookies

    me = client.get("/api/v1/users/me")
    assert me.status_code == 200
    assert me.json()["full_name"] == "Ada Lovelace"

    updated = client.patch("/api/v1/users/me", json={"full_name": "Ada Byron"})
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Ada Byron"

    old_refresh = client.cookies.get("socratia_refresh")
    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    assert client.cookies.get("socratia_refresh") != old_refresh

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    assert logout.json() == {"message": "Sesión cerrada."}

    unauthorized = client.get("/api/v1/users/me")
    assert unauthorized.status_code == 401


def test_registration_rejects_duplicate_email(client: TestClient) -> None:
    payload = {
        "email": "student@example.com",
        "full_name": "Socratia Student",
        "password": "a-secure-password",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201

    duplicate = client.post("/api/v1/auth/register", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "email_already_registered"


def test_login_rejects_invalid_credentials(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_registration_requires_fifteen_characters(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "short@example.com",
            "full_name": "Short Password",
            "password": "only-fourteen!",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "weak_password",
        "message": "La contraseña debe tener al menos 15 caracteres.",
    }


def test_registration_rejects_predictable_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "predictable@example.com",
            "full_name": "Predictable Password",
            "password": "passwordpassword",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "weak_password"


def test_password_preserves_boundary_spaces(client: TestClient) -> None:
    password = " una frase segura y memorable "
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "spaces@example.com",
            "full_name": "Password Spaces",
            "password": password,
        },
    )
    assert registration.status_code == 201

    trimmed_login = client.post(
        "/api/v1/auth/login",
        json={"email": "spaces@example.com", "password": password.strip()},
    )
    exact_login = client.post(
        "/api/v1/auth/login",
        json={"email": "spaces@example.com", "password": password},
    )

    assert trimmed_login.status_code == 401
    assert exact_login.status_code == 200


def test_login_uses_same_error_for_missing_account_and_wrong_password(
    client: TestClient,
) -> None:
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": "existing@example.com",
            "full_name": "Existing Account",
            "password": "a memorable defense phrase",
        },
    )
    assert registration.status_code == 201

    missing = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "incorrect-password"},
    )
    existing = client.post(
        "/api/v1/auth/login",
        json={"email": "existing@example.com", "password": "incorrect-password"},
    )

    assert missing.status_code == existing.status_code == 401
    assert missing.json() == existing.json()
