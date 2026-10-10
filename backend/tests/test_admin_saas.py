import pytest
from fastapi.testclient import TestClient

from app.modules.p1_gestion_identidad_seguridad.repositories.user_repository import UserRepository


def create_admin_and_login(client: TestClient, db_session) -> dict:
    repo = UserRepository(db_session)
    user = repo.get_by_email("admin@test.com")
    if not user:
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@test.com",
                "full_name": "Admin User",
                "password": "this_is_a_strong_password",
            },
        )
        user = repo.get_by_email("admin@test.com")
        role = repo.get_or_create_role("Administrator")
        user.roles.append(role)
        db_session.commit()

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "this_is_a_strong_password"},
    )
    token = resp.cookies.get("socratia_access")
    return {"Authorization": f"Bearer {token}", "user": user}


def create_student_and_login(client: TestClient, db_session) -> dict:
    repo = UserRepository(db_session)
    user = repo.get_by_email("student@test.com")
    if not user:
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "student@test.com",
                "full_name": "Student User",
                "password": "this_is_a_strong_password",
            },
        )
        user = repo.get_by_email("student@test.com")

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "student@test.com", "password": "this_is_a_strong_password"},
    )
    token = resp.cookies.get("socratia_access")
    return {"Authorization": f"Bearer {token}", "user": user}


@pytest.fixture
def admin_data(client: TestClient, db_session):
    return create_admin_and_login(client, db_session)


@pytest.fixture
def student_data(client: TestClient, db_session):
    return create_student_and_login(client, db_session)


@pytest.fixture
def admin_headers(admin_data):
    return {"Authorization": admin_data["Authorization"]}


@pytest.fixture
def student_headers(student_data):
    return {"Authorization": student_data["Authorization"]}


@pytest.fixture
def base_plan(client: TestClient, admin_headers):
    response = client.post(
        "/api/v1/admin/plans",
        headers=admin_headers,
        json={
            "name": "Base Plan",
            "description": "Base",
            "price": "10.00",
            "max_documents": 10,
            "max_simulations": 5,
            "max_storage_mb": 50,
            "is_active": True,
        },
    )
    return response.json()


def test_01_create_plan_success(client: TestClient, admin_headers):
    res = client.post(
        "/api/v1/admin/plans",
        headers=admin_headers,
        json={
            "name": "Pro Plan",
            "price": "29.99",
            "max_documents": 100,
            "max_simulations": 50,
            "max_storage_mb": 500,
            "is_active": True,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Pro Plan"


def test_02_create_plan_student_403(client: TestClient, student_headers):
    res = client.post(
        "/api/v1/admin/plans",
        headers=student_headers,
        json={"name": "Hacked Plan", "price": "0.00"},
    )
    assert res.status_code == 403


def test_03_create_plan_anon_401(client: TestClient):
    res = client.post("/api/v1/admin/plans", json={"name": "Anon", "price": "1.00"})
    assert res.status_code == 401


def test_04_create_plan_negative_price_422(client: TestClient, admin_headers):
    res = client.post(
        "/api/v1/admin/plans", headers=admin_headers, json={"name": "Freebie", "price": "-10.00"}
    )
    assert res.status_code == 422


def test_05_create_plan_extra_fields_422(client: TestClient, admin_headers):
    res = client.post(
        "/api/v1/admin/plans",
        headers=admin_headers,
        json={"name": "Extra Plan", "price": "10.00", "hacked_field": "123"},
    )
    assert res.status_code == 422


def test_06_create_plan_duplicate_name(client: TestClient, admin_headers, base_plan):
    res = client.post(
        "/api/v1/admin/plans",
        headers=admin_headers,
        json={"name": base_plan["name"], "price": "15.00"},
    )
    assert res.status_code == 400


def test_07_get_plans_admin(client: TestClient, admin_headers, base_plan):
    res = client.get("/api/v1/admin/plans", headers=admin_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_08_get_plans_student_403(client: TestClient, student_headers):
    res = client.get("/api/v1/admin/plans", headers=student_headers)
    assert res.status_code == 403


def test_09_get_plan_by_id(client: TestClient, admin_headers, base_plan):
    res = client.get(f"/api/v1/admin/plans/{base_plan['id']}", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["name"] == base_plan["name"]


def test_10_update_plan(client: TestClient, admin_headers, base_plan):
    res = client.patch(
        f"/api/v1/admin/plans/{base_plan['id']}", headers=admin_headers, json={"price": "12.00"}
    )
    assert res.status_code == 200
    assert res.json()["price"] == "12.00"


def test_11_update_plan_extra_fields_422(client: TestClient, admin_headers, base_plan):
    res = client.patch(
        f"/api/v1/admin/plans/{base_plan['id']}", headers=admin_headers, json={"hacked_id": "123"}
    )
    assert res.status_code == 422


def test_12_deactivate_plan(client: TestClient, admin_headers, base_plan):
    res = client.patch(
        f"/api/v1/admin/plans/{base_plan['id']}", headers=admin_headers, json={"is_active": False}
    )
    assert res.status_code == 200
    assert res.json()["is_active"] is False


def test_13_create_subscription_success(client: TestClient, admin_headers, base_plan, student_data):
    client.patch(
        f"/api/v1/admin/plans/{base_plan['id']}", headers=admin_headers, json={"is_active": True}
    )

    res = client.post(
        "/api/v1/admin/subscriptions",
        headers=admin_headers,
        json={"user_id": student_data["user"].id, "plan_id": base_plan["id"]},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "ACTIVE"
    assert data["price_at_subscription"] == base_plan["price"]


def test_14_create_subscription_inactive_plan(
    client: TestClient, admin_headers, base_plan, student_data
):
    client.patch(
        f"/api/v1/admin/plans/{base_plan['id']}", headers=admin_headers, json={"is_active": False}
    )

    res = client.post(
        "/api/v1/admin/subscriptions",
        headers=admin_headers,
        json={"user_id": student_data["user"].id, "plan_id": base_plan["id"]},
    )
    assert res.status_code == 400


def test_15_create_subscription_duplicate_active_400(
    client: TestClient, admin_headers, base_plan, student_data
):
    client.patch(
        f"/api/v1/admin/plans/{base_plan['id']}", headers=admin_headers, json={"is_active": True}
    )

    res1 = client.post(
        "/api/v1/admin/subscriptions",
        headers=admin_headers,
        json={"user_id": student_data["user"].id, "plan_id": base_plan["id"]},
    )
    if res1.status_code == 400:
        pass
    else:
        res2 = client.post(
            "/api/v1/admin/subscriptions",
            headers=admin_headers,
            json={"user_id": student_data["user"].id, "plan_id": base_plan["id"]},
        )
        assert res2.status_code == 400


def test_16_create_subscription_student_403(
    client: TestClient, student_headers, base_plan, student_data
):
    res = client.post(
        "/api/v1/admin/subscriptions",
        headers=student_headers,
        json={"user_id": student_data["user"].id, "plan_id": base_plan["id"]},
    )
    assert res.status_code == 403


def test_17_create_subscription_anon_401(client: TestClient, base_plan, student_data):
    client.cookies.clear()
    res = client.post(
        "/api/v1/admin/subscriptions",
        json={"user_id": student_data["user"].id, "plan_id": base_plan["id"]},
    )
    assert res.status_code == 401


def test_18_create_subscription_extra_fields_422(
    client: TestClient, admin_headers, base_plan, student_data
):
    res = client.post(
        "/api/v1/admin/subscriptions",
        headers=admin_headers,
        json={
            "user_id": student_data["user"].id,
            "plan_id": base_plan["id"],
            "price_at_subscription": "0.00",
        },
    )
    assert res.status_code == 422


def test_19_get_subscriptions_admin(client: TestClient, admin_headers):
    res = client.get("/api/v1/admin/subscriptions", headers=admin_headers)
    assert res.status_code == 200


def test_20_get_subscriptions_student_403(client: TestClient, student_headers):
    res = client.get("/api/v1/admin/subscriptions", headers=student_headers)
    assert res.status_code == 403


def test_21_cancel_subscription_keeps_history(
    client: TestClient, admin_headers, base_plan, student_data
):
    client.patch(
        f"/api/v1/admin/plans/{base_plan['id']}", headers=admin_headers, json={"is_active": True}
    )

    subs = client.get("/api/v1/admin/subscriptions", headers=admin_headers)
    for sub in subs.json():
        if sub["user_id"] == student_data["user"].id and sub["status"] == "ACTIVE":
            client.patch(
                f"/api/v1/admin/subscriptions/{sub['id']}",
                headers=admin_headers,
                json={"status": "CANCELLED"},
            )

    res = client.post(
        "/api/v1/admin/subscriptions",
        headers=admin_headers,
        json={"user_id": student_data["user"].id, "plan_id": base_plan["id"]},
    )
    assert res.status_code == 201
    sub_id = res.json()["id"]

    cancel_res = client.patch(
        f"/api/v1/admin/subscriptions/{sub_id}", headers=admin_headers, json={"status": "CANCELLED"}
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"
    assert cancel_res.json()["cancelled_at"] is not None

    get_res = client.get(f"/api/v1/admin/subscriptions/{sub_id}", headers=admin_headers)
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "CANCELLED"


def test_22_update_subscription_extra_fields(
    client: TestClient, admin_headers, base_plan, student_data
):
    subs = client.get("/api/v1/admin/subscriptions", headers=admin_headers)
    sub_id = subs.json()[0]["id"] if subs.json() else "fake-id"
    if sub_id != "fake-id":
        res = client.patch(
            f"/api/v1/admin/subscriptions/{sub_id}",
            headers=admin_headers,
            json={"hacked_field": True},
        )
        assert res.status_code == 422


def test_23_update_subscription_change_plan(
    client: TestClient, admin_headers, base_plan, student_data
):
    plan2_res = client.post(
        "/api/v1/admin/plans",
        headers=admin_headers,
        json={"name": "Another Plan 2", "price": "9.99"},
    )
    plan2 = plan2_res.json()

    subs = client.get("/api/v1/admin/subscriptions", headers=admin_headers)
    for sub in subs.json():
        if sub["user_id"] == student_data["user"].id and sub["status"] == "ACTIVE":
            client.patch(
                f"/api/v1/admin/subscriptions/{sub['id']}",
                headers=admin_headers,
                json={"status": "CANCELLED"},
            )

    sub_res = client.post(
        "/api/v1/admin/subscriptions",
        headers=admin_headers,
        json={"user_id": student_data["user"].id, "plan_id": base_plan["id"]},
    )
    sub_id = sub_res.json()["id"]

    up_res = client.patch(
        f"/api/v1/admin/subscriptions/{sub_id}",
        headers=admin_headers,
        json={"plan_id": plan2["id"]},
    )
    assert up_res.status_code == 200
    assert up_res.json()["plan_id"] == plan2["id"]


def test_24_update_subscription_change_plan_inactive(
    client: TestClient, admin_headers, base_plan, student_data
):
    plan2_res = client.post(
        "/api/v1/admin/plans",
        headers=admin_headers,
        json={"name": "Inactive Plan 2", "price": "9.99", "is_active": False},
    )
    plan2 = plan2_res.json()

    subs = client.get("/api/v1/admin/subscriptions", headers=admin_headers)
    sub = next((s for s in subs.json() if s["status"] == "ACTIVE"), None)
    if sub:
        up_res = client.patch(
            f"/api/v1/admin/subscriptions/{sub['id']}",
            headers=admin_headers,
            json={"plan_id": plan2["id"]},
        )
        assert up_res.status_code == 400


def test_25_admin_dashboard_integration(client: TestClient, admin_headers):
    res = client.get("/api/v1/admin/users", headers=admin_headers)
    assert res.status_code == 200
