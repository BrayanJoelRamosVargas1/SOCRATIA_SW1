import pytest
from fastapi.testclient import TestClient

from app.modules.p1_gestion_identidad_seguridad.repositories.user_repository import UserRepository


def create_user_and_login(client: TestClient, db_session, email: str, role_name: str | None = None) -> dict:
    repo = UserRepository(db_session)
    user = repo.get_by_email(email)
    if not user:
        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "full_name": email.split("@")[0].capitalize(),
                "password": "this_is_a_strong_password",
            },
        )
        user = repo.get_by_email(email)
        if role_name:
            role = repo.get_or_create_role(role_name)
            user.roles.append(role)
            db_session.commit()

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "this_is_a_strong_password"},
    )
    token = resp.cookies.get("socratia_access")
    return {"headers": {"Authorization": f"Bearer {token}"}, "user": user}


@pytest.fixture
def student_a(client: TestClient, db_session):
    return create_user_and_login(client, db_session, "student_a@test.com")


@pytest.fixture
def student_b(client: TestClient, db_session):
    return create_user_and_login(client, db_session, "student_b@test.com")


@pytest.fixture
def admin_user(client: TestClient, db_session):
    return create_user_and_login(client, db_session, "admin_sub@test.com", "Administrator")


@pytest.fixture
def setup_plans(client: TestClient, admin_user):
    # Create Basic active plan
    res_basic = client.post(
        "/api/v1/admin/plans",
        headers=admin_user["headers"],
        json={"name": "Basic Plan", "price": "10.00", "is_active": True},
    )
    basic_plan = res_basic.json()

    # Create Pro active plan
    res_pro = client.post(
        "/api/v1/admin/plans",
        headers=admin_user["headers"],
        json={"name": "Pro Plan", "price": "25.00", "is_active": True},
    )
    pro_plan = res_pro.json()

    # Create Inactive plan
    res_inactive = client.post(
        "/api/v1/admin/plans",
        headers=admin_user["headers"],
        json={"name": "Legacy Plan", "price": "5.00", "is_active": False},
    )
    inactive_plan = res_inactive.json()

    return {"basic": basic_plan, "pro": pro_plan, "inactive": inactive_plan}


def test_01_list_only_active_plans(client: TestClient, student_a, setup_plans):
    res = client.get("/api/v1/plans", headers=student_a["headers"])
    assert res.status_code == 200
    plans = res.json()
    assert len(plans) >= 2
    for p in plans:
        assert p["is_active"] is True
        assert p["id"] != setup_plans["inactive"]["id"]


def test_02_get_subscription_none_initially(client: TestClient, student_a, setup_plans):
    res = client.get("/api/v1/subscription", headers=student_a["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["subscription"] is None
    assert data["plan"] is None
    assert len(data["history"]) == 0


def test_03_subscribe_initial_success(client: TestClient, student_a, setup_plans):
    basic = setup_plans["basic"]
    res = client.post(
        "/api/v1/subscription",
        headers=student_a["headers"],
        json={"plan_id": basic["id"]},
    )
    assert res.status_code == 201
    sub = res.json()
    assert sub["status"] == "ACTIVE"
    assert sub["plan_id"] == basic["id"]
    assert sub["user_id"] == student_a["user"].id
    assert sub["price_at_subscription"] == basic["price"]


def test_04_get_subscription_after_subscribe(client: TestClient, student_a, setup_plans):
    basic = setup_plans["basic"]
    client.post(
        "/api/v1/subscription",
        headers=student_a["headers"],
        json={"plan_id": basic["id"]},
    )
    res = client.get("/api/v1/subscription", headers=student_a["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["subscription"] is not None
    assert data["subscription"]["status"] == "ACTIVE"
    assert data["plan"]["name"] == "Basic Plan"


def test_05_reject_invalid_plan(client: TestClient, student_b, setup_plans):
    res = client.post(
        "/api/v1/subscription",
        headers=student_b["headers"],
        json={"plan_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert res.status_code == 404


def test_06_reject_inactive_plan(client: TestClient, student_b, setup_plans):
    res = client.post(
        "/api/v1/subscription",
        headers=student_b["headers"],
        json={"plan_id": setup_plans["inactive"]["id"]},
    )
    assert res.status_code == 400


def test_07_prevent_second_active_subscription(client: TestClient, student_a, setup_plans):
    # First active subscription
    client.post(
        "/api/v1/subscription",
        headers=student_a["headers"],
        json={"plan_id": setup_plans["basic"]["id"]},
    )
    # Attempt second active subscription
    res = client.post(
        "/api/v1/subscription",
        headers=student_a["headers"],
        json={"plan_id": setup_plans["pro"]["id"]},
    )
    assert res.status_code == 400


def test_08_change_plan_preserves_history(client: TestClient, student_a, setup_plans):
    # 1. Student subscribes to BASIC ($10.00)
    basic = setup_plans["basic"]
    res_init = client.post(
        "/api/v1/subscription",
        headers=student_a["headers"],
        json={"plan_id": basic["id"]},
    )
    assert res_init.status_code == 201

    # 2. Change plan to PRO ($25.00)
    pro = setup_plans["pro"]
    res = client.patch(
        "/api/v1/subscription",
        headers=student_a["headers"],
        json={"plan_id": pro["id"]},
    )
    assert res.status_code == 200
    new_sub = res.json()
    assert new_sub["status"] == "ACTIVE"
    assert new_sub["plan_id"] == pro["id"]
    assert new_sub["price_at_subscription"] == pro["price"]

    # 3. Verify history via GET
    get_res = client.get("/api/v1/subscription", headers=student_a["headers"])
    data = get_res.json()
    assert data["subscription"]["plan_id"] == pro["id"]
    assert data["subscription"]["status"] == "ACTIVE"

    # Crucial assertion: exactly 1 ACTIVE subscription exists, and history contains BASIC (cancelled)
    history = data["history"]
    assert len(history) == 2
    active_subs = [s for s in history if s["status"] == "ACTIVE"]
    cancelled_subs = [s for s in history if s["status"] == "CANCELLED"]

    assert len(active_subs) == 1
    assert active_subs[0]["plan_id"] == pro["id"]

    assert len(cancelled_subs) == 1
    assert cancelled_subs[0]["plan_id"] == setup_plans["basic"]["id"]
    assert cancelled_subs[0]["price_at_subscription"] == setup_plans["basic"]["price"]
    assert cancelled_subs[0]["cancelled_at"] is not None


def test_09_reject_change_to_same_plan(client: TestClient, student_a, setup_plans):
    # Subscribe to PRO
    pro = setup_plans["pro"]
    client.post(
        "/api/v1/subscription",
        headers=student_a["headers"],
        json={"plan_id": pro["id"]},
    )
    # Attempt change to PRO again
    res = client.patch(
        "/api/v1/subscription",
        headers=student_a["headers"],
        json={"plan_id": pro["id"]},
    )
    assert res.status_code == 400


def test_10_cancel_subscription(client: TestClient, student_a, setup_plans):
    # Subscribe first
    client.post(
        "/api/v1/subscription",
        headers=student_a["headers"],
        json={"plan_id": setup_plans["basic"]["id"]},
    )
    # Cancel
    res = client.post("/api/v1/subscription/cancel", headers=student_a["headers"])
    assert res.status_code == 200
    cancelled = res.json()
    assert cancelled["status"] == "CANCELLED"
    assert cancelled["cancelled_at"] is not None

    # Check that currently there is NO active subscription
    get_res = client.get("/api/v1/subscription", headers=student_a["headers"])
    data = get_res.json()
    assert data["subscription"] is None

    # History preserves the subscription
    history = data["history"]
    assert len(history) == 1
    assert history[0]["status"] == "CANCELLED"
    assert history[0]["price_at_subscription"] == setup_plans["basic"]["price"]


def test_11_second_cancel_handled_gracefully(client: TestClient, student_a, setup_plans):
    # Subscribe
    client.post(
        "/api/v1/subscription",
        headers=student_a["headers"],
        json={"plan_id": setup_plans["basic"]["id"]},
    )
    # First cancel -> 200
    res1 = client.post("/api/v1/subscription/cancel", headers=student_a["headers"])
    assert res1.status_code == 200
    # Second cancel -> 400 (no active subscription)
    res2 = client.post("/api/v1/subscription/cancel", headers=student_a["headers"])
    assert res2.status_code == 400


def test_12_extra_fields_rejected_422(client: TestClient, student_b, setup_plans):
    res = client.post(
        "/api/v1/subscription",
        headers=student_b["headers"],
        json={"plan_id": setup_plans["basic"]["id"], "user_id": "hacked_id"},
    )
    assert res.status_code == 422


def test_13_extra_fields_on_change_rejected_422(client: TestClient, student_b, setup_plans):
    res = client.patch(
        "/api/v1/subscription",
        headers=student_b["headers"],
        json={"plan_id": setup_plans["pro"]["id"], "role": "admin"},
    )
    assert res.status_code == 422


def test_14_anonymous_rejected_401(client: TestClient, setup_plans):
    client.cookies.clear()
    res = client.get("/api/v1/subscription")
    assert res.status_code == 401

    res = client.post("/api/v1/subscription", json={"plan_id": setup_plans["basic"]["id"]})
    assert res.status_code == 401

    res = client.patch("/api/v1/subscription", json={"plan_id": setup_plans["pro"]["id"]})
    assert res.status_code == 401

    res = client.post("/api/v1/subscription/cancel")
    assert res.status_code == 401


def test_15_tenant_isolation_students_isolated(client: TestClient, student_a, student_b, setup_plans):
    # Student B subscribes to Basic
    res_b = client.post(
        "/api/v1/subscription",
        headers=student_b["headers"],
        json={"plan_id": setup_plans["basic"]["id"]},
    )
    assert res_b.status_code == 201

    # Student A inspects their own subscription -> remains None
    res_a = client.get("/api/v1/subscription", headers=student_a["headers"])
    assert res_a.status_code == 200
    assert res_a.json()["subscription"] is None

    # Student B gets their active subscription
    data_b = client.get("/api/v1/subscription", headers=student_b["headers"]).json()
    assert data_b["subscription"]["id"] == res_b.json()["id"]
    assert data_b["subscription"]["user_id"] == student_b["user"].id


def test_16_student_cannot_access_admin_endpoints(client: TestClient, student_a, setup_plans):
    res = client.get("/api/v1/admin/plans", headers=student_a["headers"])
    assert res.status_code == 403

    res = client.get("/api/v1/admin/subscriptions", headers=student_a["headers"])
    assert res.status_code == 403
