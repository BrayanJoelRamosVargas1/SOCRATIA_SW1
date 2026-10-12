import concurrent.futures
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.modules.p1_gestion_identidad_seguridad.repositories.user_repository import UserRepository
from app.modules.p5_gestion_saas.models.plan import Plan
from app.modules.p5_gestion_saas.models.subscription import Subscription, SubscriptionStatus
from app.modules.p5_gestion_saas.services.subscription_service import SubscriptionService


def test_concurrent_subscriptions_db_unique_index(db_session: Session):
    # 1. Setup user and plan directly in DB
    repo = UserRepository(db_session)
    user = repo.create(email="concurrent_student@test.com", full_name="Concurrent Student", password_hash="fake_hash")
    plan = Plan(name="Concurrency Plan", price=Decimal("19.99"), is_active=True)
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(plan)

    # 2. First active subscription succeeds
    sub1 = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        price_at_subscription=plan.price,
    )
    db_session.add(sub1)
    db_session.commit()

    # 3. Second active subscription directly at DB level must violate partial unique index
    sub2 = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        price_at_subscription=plan.price,
    )
    db_session.add(sub2)
    with pytest.raises(Exception) as excinfo:
        db_session.commit()

    assert "uq_active_user_subscription" in str(excinfo.value).lower() or "unique" in str(excinfo.value).lower()
    db_session.rollback()

    # 4. Inactive or cancelled subscriptions for the SAME user CAN coexist (partial index property)
    sub_cancelled = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        status=SubscriptionStatus.CANCELLED,
        price_at_subscription=plan.price,
    )
    db_session.add(sub_cancelled)
    db_session.commit()  # Must NOT raise

    # 5. Exactly 1 ACTIVE subscription exists in DB
    count = db_session.execute(
        text("SELECT count(*) FROM subscriptions WHERE user_id = :uid AND status = 'ACTIVE'"),
        {"uid": user.id},
    ).scalar()
    assert count == 1


def test_concurrent_service_calls(db_session: Session):
    """Verifies that two concurrent SubscriptionService calls with independent DB sessions

    are safely governed by PostgreSQL's partial unique index, returning 409 for the loser.
    """
    engine = db_session.bind
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    repo = UserRepository(db_session)
    user = repo.create(
        email="concurrent_service@test.com",
        full_name="Concurrent Service Student",
        password_hash="fake_hash",
    )
    plan = Plan(name="Service Concurrency Plan", price=Decimal("15.00"), is_active=True)
    db_session.add(plan)
    db_session.commit()

    results = []

    def run_subscribe():
        s = session_factory()
        try:
            sub = SubscriptionService.subscribe_student(s, user.id, plan.id)
            results.append(("SUCCESS", sub.id))
        except Exception as exc:
            results.append(("ERROR", type(exc).__name__, getattr(exc, "status_code", None)))
        finally:
            s.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_subscribe)
        f2 = executor.submit(run_subscribe)
        f1.result()
        f2.result()

    successes = [r for r in results if r[0] == "SUCCESS"]
    errors = [r for r in results if r[0] == "ERROR"]

    # Exactly 1 success, and 1 error (HTTPException with 409 Conflict or 400 Bad Request)
    assert len(successes) == 1
    assert len(errors) == 1
    assert errors[0][2] in (400, 409)

    # Invariant: exactly 1 active subscription in DB
    count = db_session.execute(
        text("SELECT count(*) FROM subscriptions WHERE user_id = :uid AND status = 'ACTIVE'"),
        {"uid": user.id},
    ).scalar()
    assert count == 1


def test_concurrent_http_subscription_requests(client: TestClient, db_session: Session):
    from app.core.database import get_db

    # Register student via API
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "concurrent_http@test.com",
            "full_name": "Concurrent HTTP",
            "password": "this_is_a_strong_password",
        },
    )
    repo = UserRepository(db_session)
    user = repo.get_by_email("concurrent_http@test.com")
    plan = Plan(name="HTTP Concurrency Plan", price=Decimal("29.99"), is_active=True)
    db_session.add(plan)
    db_session.commit()

    # Login student
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "concurrent_http@test.com", "password": "this_is_a_strong_password"},
    )
    token = resp.cookies.get("socratia_access")
    headers = {"Authorization": f"Bearer {token}"}

    # Setup thread-safe sessionmaker for concurrent HTTP requests
    engine = db_session.bind
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def threadsafe_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    # Provide threadsafe sessions during concurrency execution
    client.app.dependency_overrides[get_db] = threadsafe_get_db

    try:
        def send_sub():
            with TestClient(client.app, cookies={"socratia_access": token}) as c:
                return c.post("/api/v1/subscription/", headers=headers, json={"plan_id": plan.id})

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(send_sub)
            future2 = executor.submit(send_sub)
            res1 = future1.result()
            res2 = future2.result()

        statuses = [res1.status_code, res2.status_code]
        assert 201 in statuses
        assert (400 in statuses) or (409 in statuses)

        # Database invariant: exactly 1 ACTIVE subscription
        count = db_session.execute(
            text("SELECT count(*) FROM subscriptions WHERE user_id = :uid AND status = 'ACTIVE'"),
            {"uid": user.id},
        ).scalar()
        assert count == 1
    finally:
        # Restore default test db_session override
        def override_get_db():
            yield db_session

        client.app.dependency_overrides[get_db] = override_get_db
