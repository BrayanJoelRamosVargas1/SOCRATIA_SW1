from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.models.document import Document
from app.modules.p2_gestion_documentos_preparacion.models.question_bank import QuestionBank
from app.modules.p3_gestion_simulacion.models.simulation import (
    FocusType,
    InterruptionLevel,
    JuryProfile,
    Simulation,
    SimulationStatus,
)
from app.modules.p4_gestion_evaluacion_resultados.models.evaluation import (
    Evaluation,
    EvaluationStatus,
)


@pytest.fixture
def test_user(db_session: Session):
    user = User(id=str(uuid4()), email="test@test.com", full_name="Test", password_hash="pw")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(user_id=test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def setup_data(db_session: Session, test_user: User):
    doc1 = Document(
        id=str(uuid4()),
        user_id=test_user.id,
        original_name="Doc 1",
        file_type="pdf",
        file_size=1,
        content_hash="hash",
        storage_key="key1",
        status="PROCESSED",
    )
    doc2 = Document(
        id=str(uuid4()),
        user_id=test_user.id,
        original_name="Doc 2",
        file_type="pdf",
        file_size=1,
        content_hash="hash2",
        storage_key="key2",
        status="PROCESSED",
    )
    db_session.add(doc1)
    db_session.add(doc2)

    bank = QuestionBank(id=str(uuid4()), document_id=doc1.id, user_id=test_user.id)
    db_session.add(bank)

    jury = JuryProfile(
        id=str(uuid4()),
        name="Jury",
        description="Test",
        focus_type=FocusType.TECHNICAL,
        strictness=3,
        interruption_level=InterruptionLevel.LOW,
    )
    db_session.add(jury)
    db_session.commit()

    return {"doc1": doc1, "doc2": doc2, "bank": bank, "jury": jury}


def create_simulation(
    db_session, user, doc, bank, jury, status, created_at, started_at=None, finished_at=None
):
    sim = Simulation(
        id=str(uuid4()),
        user_id=user.id,
        document_id=doc.id,
        question_bank_id=bank.id,
        jury_profile_id=jury.id,
        status=status,
        planned_duration_minutes=10,
        created_at=created_at,
        started_at=started_at,
        finished_at=finished_at,
    )
    db_session.add(sim)
    db_session.commit()
    db_session.refresh(sim)
    return sim


def create_evaluation(db_session, sim, status, score=None):
    ev = Evaluation(
        id=str(uuid4()),
        simulation_id=sim.id,
        status=status,
        overall_score=score,
        content_score=score,
        communication_score=score,
        nonverbal_score=score,
    )
    db_session.add(ev)
    db_session.commit()
    db_session.refresh(ev)
    return ev


def test_history_empty_for_new_user(client: TestClient, auth_headers):
    response = client.get("/api/v1/performance-history", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total_items"] == 0


def test_history_returns_correct_summary_totals(
    client: TestClient, db_session: Session, test_user: User, setup_data, auth_headers
):
    # Create 3 simulations, 2 evaluated
    now = datetime.now(UTC)
    s1 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now - timedelta(days=2),
    )
    create_evaluation(db_session, s1, EvaluationStatus.COMPLETED, 80.0)

    s2 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now - timedelta(days=1),
    )
    create_evaluation(db_session, s2, EvaluationStatus.COMPLETED, 90.0)

    s3 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.DRAFT,
        now,
    )

    response = client.get("/api/v1/performance-history", headers=auth_headers)
    data = response.json()
    assert data["summary"]["total_simulations"] == 3
    assert data["summary"]["evaluated_simulations"] == 2


def test_history_returns_latest_and_best_scores(
    client, db_session, test_user, setup_data, auth_headers
):
    now = datetime.now(UTC)
    s1 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now - timedelta(days=2),
    )
    create_evaluation(db_session, s1, EvaluationStatus.COMPLETED, 95.0)

    s2 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now - timedelta(days=1),
    )
    create_evaluation(db_session, s2, EvaluationStatus.COMPLETED, 85.0)

    response = client.get("/api/v1/performance-history", headers=auth_headers)
    data = response.json()
    assert data["summary"]["best_score"] == 95.0
    assert data["summary"]["latest_score"] == 85.0


def test_history_pagination_default(client, db_session, test_user, setup_data, auth_headers):
    for i in range(12):
        s = create_simulation(
            db_session,
            test_user,
            setup_data["doc1"],
            setup_data["bank"],
            setup_data["jury"],
            SimulationStatus.COMPLETED,
            datetime.now(UTC),
        )
    response = client.get("/api/v1/performance-history", headers=auth_headers)
    assert len(response.json()["items"]) == 10
    assert response.json()["total_items"] == 12


def test_history_pagination_custom_size(client, db_session, test_user, setup_data, auth_headers):
    for i in range(5):
        s = create_simulation(
            db_session,
            test_user,
            setup_data["doc1"],
            setup_data["bank"],
            setup_data["jury"],
            SimulationStatus.COMPLETED,
            datetime.now(UTC),
        )
    response = client.get("/api/v1/performance-history?page_size=2", headers=auth_headers)
    assert len(response.json()["items"]) == 2


def test_history_pagination_page_2(client, db_session, test_user, setup_data, auth_headers):
    for i in range(5):
        s = create_simulation(
            db_session,
            test_user,
            setup_data["doc1"],
            setup_data["bank"],
            setup_data["jury"],
            SimulationStatus.COMPLETED,
            datetime.now(UTC),
        )
    response = client.get("/api/v1/performance-history?page_size=2&page=3", headers=auth_headers)
    assert len(response.json()["items"]) == 1


def test_history_pagination_calculates_total_pages_correctly(
    client, db_session, test_user, setup_data, auth_headers
):
    for i in range(5):
        s = create_simulation(
            db_session,
            test_user,
            setup_data["doc1"],
            setup_data["bank"],
            setup_data["jury"],
            SimulationStatus.COMPLETED,
            datetime.now(UTC),
        )
    response = client.get("/api/v1/performance-history?page_size=2", headers=auth_headers)
    assert response.json()["total_pages"] == 3


def test_history_filter_by_document_id(client, db_session, test_user, setup_data, auth_headers):
    s1 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        datetime.now(UTC),
    )
    s2 = create_simulation(
        db_session,
        test_user,
        setup_data["doc2"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        datetime.now(UTC),
    )

    response = client.get(
        f"/api/v1/performance-history?document_id={setup_data['doc1'].id}", headers=auth_headers
    )
    assert response.json()["total_items"] == 1
    assert response.json()["items"][0]["simulation_id"] == s1.id


def test_history_filter_by_status_completed(
    client, db_session, test_user, setup_data, auth_headers
):
    s1 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        datetime.now(UTC),
    )
    s2 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.DRAFT,
        datetime.now(UTC),
    )

    response = client.get("/api/v1/performance-history?status=COMPLETED", headers=auth_headers)
    assert response.json()["total_items"] == 1
    assert response.json()["items"][0]["simulation_id"] == s1.id


def test_history_filter_by_status_pending(client, db_session, test_user, setup_data, auth_headers):
    s1 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        datetime.now(UTC),
    )
    create_evaluation(db_session, s1, EvaluationStatus.PENDING)

    response = client.get("/api/v1/performance-history?status=PENDING", headers=auth_headers)
    assert response.json()["total_items"] == 1
    assert response.json()["items"][0]["simulation_id"] == s1.id


def test_history_filter_by_start_date(client, db_session, test_user, setup_data, auth_headers):
    now = datetime.now(UTC)
    create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now - timedelta(days=2),
    )
    create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now,
    )

    import urllib.parse

    d_str = urllib.parse.quote((now - timedelta(days=1)).isoformat())
    response = client.get(f"/api/v1/performance-history?start_date={d_str}", headers=auth_headers)
    assert response.json()["total_items"] == 1


def test_history_filter_by_end_date(client, db_session, test_user, setup_data, auth_headers):
    now = datetime.now(UTC)
    create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now - timedelta(days=2),
    )
    create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now,
    )

    import urllib.parse

    d_str = urllib.parse.quote((now - timedelta(days=1)).isoformat())
    response = client.get(f"/api/v1/performance-history?end_date={d_str}", headers=auth_headers)
    assert response.json()["total_items"] == 1


def test_history_filter_by_date_range(client, db_session, test_user, setup_data, auth_headers):
    now = datetime.now(UTC)
    create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now - timedelta(days=3),
    )
    s2 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now - timedelta(days=2),
    )
    create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now,
    )

    import urllib.parse

    start_str = urllib.parse.quote((now - timedelta(days=2, hours=1)).isoformat())
    end_str = urllib.parse.quote((now - timedelta(days=1)).isoformat())
    response = client.get(
        f"/api/v1/performance-history?start_date={start_str}&end_date={end_str}",
        headers=auth_headers,
    )
    assert response.json()["total_items"] == 1
    assert response.json()["items"][0]["simulation_id"] == s2.id


def test_history_delta_is_none_for_first_simulation(
    client, db_session, test_user, setup_data, auth_headers
):
    now = datetime.now(UTC)
    s1 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now,
    )
    create_evaluation(db_session, s1, EvaluationStatus.COMPLETED, 80.0)

    response = client.get("/api/v1/performance-history", headers=auth_headers)
    assert response.json()["items"][0]["delta_score"] is None


def test_history_delta_positive_improvement(
    client, db_session, test_user, setup_data, auth_headers
):
    now = datetime.now(UTC)
    s1 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now - timedelta(days=1),
    )
    create_evaluation(db_session, s1, EvaluationStatus.COMPLETED, 80.0)

    s2 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now,
    )
    create_evaluation(db_session, s2, EvaluationStatus.COMPLETED, 90.0)

    response = client.get("/api/v1/performance-history", headers=auth_headers)
    items = response.json()["items"]
    # items are desc, so items[0] is s2
    assert items[0]["delta_score"] == 10.0


def test_history_delta_negative_decrease(client, db_session, test_user, setup_data, auth_headers):
    now = datetime.now(UTC)
    s1 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now - timedelta(days=1),
    )
    create_evaluation(db_session, s1, EvaluationStatus.COMPLETED, 90.0)

    s2 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now,
    )
    create_evaluation(db_session, s2, EvaluationStatus.COMPLETED, 85.0)

    response = client.get("/api/v1/performance-history", headers=auth_headers)
    items = response.json()["items"]
    assert items[0]["delta_score"] == -5.0


def test_history_delta_zero_no_change(client, db_session, test_user, setup_data, auth_headers):
    now = datetime.now(UTC)
    s1 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now - timedelta(days=1),
    )
    create_evaluation(db_session, s1, EvaluationStatus.COMPLETED, 90.0)

    s2 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now,
    )
    create_evaluation(db_session, s2, EvaluationStatus.COMPLETED, 90.0)

    response = client.get("/api/v1/performance-history", headers=auth_headers)
    items = response.json()["items"]
    assert items[0]["delta_score"] == 0.0


def test_history_delta_ignores_null_scores(client, db_session, test_user, setup_data, auth_headers):
    now = datetime.now(UTC)
    s1 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now - timedelta(days=2),
    )
    create_evaluation(db_session, s1, EvaluationStatus.COMPLETED, 70.0)

    s2 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now - timedelta(days=1),
    )
    create_evaluation(db_session, s2, EvaluationStatus.PENDING, None)

    s3 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now,
    )
    create_evaluation(db_session, s3, EvaluationStatus.COMPLETED, 80.0)

    response = client.get("/api/v1/performance-history", headers=auth_headers)
    items = response.json()["items"]
    # items[0] = s3, items[1] = s2, items[2] = s1
    assert items[0]["delta_score"] == 10.0  # Compared to s1, ignoring s2


def test_history_item_contains_all_scores_if_completed(
    client, db_session, test_user, setup_data, auth_headers
):
    now = datetime.now(UTC)
    s1 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now,
    )
    create_evaluation(db_session, s1, EvaluationStatus.COMPLETED, 80.0)

    response = client.get("/api/v1/performance-history", headers=auth_headers)
    item = response.json()["items"][0]
    assert item["overall_score"] == 80.0
    assert item["content_score"] == 80.0


def test_history_item_scores_are_null_if_pending(
    client, db_session, test_user, setup_data, auth_headers
):
    now = datetime.now(UTC)
    s1 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now,
    )
    create_evaluation(db_session, s1, EvaluationStatus.PENDING, None)

    response = client.get("/api/v1/performance-history", headers=auth_headers)
    item = response.json()["items"][0]
    assert item["overall_score"] is None


def test_history_item_scores_are_null_if_failed(
    client, db_session, test_user, setup_data, auth_headers
):
    now = datetime.now(UTC)
    s1 = create_simulation(
        db_session,
        test_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now,
    )
    create_evaluation(db_session, s1, EvaluationStatus.FAILED, None)

    response = client.get("/api/v1/performance-history", headers=auth_headers)
    item = response.json()["items"][0]
    assert item["overall_score"] is None


def test_history_tenant_isolation_cannot_see_other_user_history(
    client, db_session, test_user, setup_data, auth_headers
):
    other_user = User(
        id=str(uuid4()), email="other@example.com", full_name="Other", password_hash="pw"
    )
    db_session.add(other_user)
    db_session.commit()

    now = datetime.now(UTC)
    create_simulation(
        db_session,
        other_user,
        setup_data["doc1"],
        setup_data["bank"],
        setup_data["jury"],
        SimulationStatus.COMPLETED,
        now,
    )

    response = client.get("/api/v1/performance-history", headers=auth_headers)
    assert response.json()["total_items"] == 0
