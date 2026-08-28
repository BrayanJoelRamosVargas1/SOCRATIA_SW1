from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.p1_gestion_identidad_seguridad.models.login_security import (
    AuthenticationEvent,
    AuthenticationEventType,
    LoginSecurity,
)


def register_account(
    client: TestClient,
    email: str,
    password: str = "a memorable defense phrase",
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Login Security", "password": password},
    )
    assert response.status_code == 201


def fail_login(client: TestClient, email: str, *, ip_address: str = "198.51.100.10"):
    return client.post(
        "/api/v1/auth/login",
        headers={"x-forwarded-for": ip_address},
        json={"email": email, "password": "incorrect-password"},
    )


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


def test_login_locks_after_three_failures(
    client: TestClient,
    db_session: Session,
) -> None:
    email = "locked@example.com"
    password = "a memorable locked phrase"
    register_account(client, email, password)

    failures = [fail_login(client, email) for _ in range(3)]
    state = db_session.scalar(select(LoginSecurity))
    assert state is not None
    assert all(response.status_code == 401 for response in failures)
    assert state.failed_attempts == 3
    assert state.lock_level == 1
    assert state.locked_until is not None
    assert state.locked_until > datetime.now(UTC)

    locked = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert locked.status_code == 401
    assert locked.json() == failures[-1].json()

    event_types = list(
        db_session.scalars(
            select(AuthenticationEvent.event_type).order_by(AuthenticationEvent.created_at)
        )
    )
    assert AuthenticationEventType.LOGIN_LOCKED.value in event_types
    assert AuthenticationEventType.LOGIN_REJECTED_LOCKED.value in event_types


def test_login_lock_escalates_to_ten_and_fifteen_minutes(
    client: TestClient,
    db_session: Session,
) -> None:
    email = "escalation@example.com"
    register_account(client, email)
    for _ in range(3):
        assert fail_login(client, email).status_code == 401

    state = db_session.scalar(select(LoginSecurity))
    assert state is not None
    state.locked_until = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()

    before_fourth = datetime.now(UTC)
    assert fail_login(client, email).status_code == 401
    assert state.failed_attempts == 4
    assert state.lock_level == 2
    assert state.locked_until is not None
    assert state.locked_until >= before_fourth + timedelta(minutes=9, seconds=55)

    state.locked_until = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()
    before_fifth = datetime.now(UTC)
    assert fail_login(client, email).status_code == 401
    assert state.failed_attempts == 5
    assert state.lock_level == 3
    assert state.locked_until is not None
    assert state.locked_until >= before_fifth + timedelta(minutes=14, seconds=55)


def test_successful_login_resets_failed_attempts(
    client: TestClient,
    db_session: Session,
) -> None:
    email = "reset-attempts@example.com"
    password = "a memorable successful phrase"
    register_account(client, email, password)
    assert fail_login(client, email).status_code == 401
    assert fail_login(client, email).status_code == 401

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    state = db_session.scalar(select(LoginSecurity))
    assert response.status_code == 200
    assert state is not None
    assert state.failed_attempts == 0
    assert state.lock_level == 0
    assert state.locked_until is None
    assert state.last_failed_at is None


def test_login_escalation_resets_after_twenty_four_hours(
    client: TestClient,
    db_session: Session,
) -> None:
    email = "observation-window@example.com"
    register_account(client, email)
    for _ in range(3):
        assert fail_login(client, email).status_code == 401

    state = db_session.scalar(select(LoginSecurity))
    assert state is not None
    state.locked_until = datetime.now(UTC) - timedelta(hours=25)
    state.last_failed_at = datetime.now(UTC) - timedelta(hours=25)
    db_session.commit()

    assert fail_login(client, email).status_code == 401
    assert state.failed_attempts == 1
    assert state.lock_level == 0
    assert state.locked_until is None


def test_login_rate_limit_uses_sliding_ip_window(
    client: TestClient,
    monkeypatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "login_ip_max_attempts", 5)
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    ip_address = "203.0.113.77"

    for index in range(5):
        response = fail_login(client, f"missing-{index}@example.com", ip_address=ip_address)
        assert response.status_code == 401

    limited = fail_login(client, "missing-final@example.com", ip_address=ip_address)
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "login_rate_limited"
