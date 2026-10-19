from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect
from test_simulation_configuration import create, profiles, ready_document, register

from app.modules.p3_gestion_simulacion.models import (
    SimulationQuestion,
    SimulationQuestionStatus,
    SimulationTurn,
    SimulationTurnState,
    SimulationTurnType,
)

ALLOWED_ORIGIN = "http://localhost:3000"


def ready_simulation(client: TestClient, email: str) -> str:
    document_id = ready_document(client, email)
    simulation_id = create(client, document_id, profiles(client)[0]["id"]).json()["id"]
    response = client.put(
        f"/api/v1/simulations/{simulation_id}/calibration",
        json={"camera_ready": True, "microphone_ready": True, "vision_ready": True},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "READY"
    return simulation_id


def start(client: TestClient, simulation_id: str) -> dict:
    response = client.post(f"/api/v1/simulations/{simulation_id}/start")
    assert response.status_code == 200
    return response.json()


def receive_initial(websocket) -> tuple[dict, dict]:
    snapshot = websocket.receive_json()
    question = websocket.receive_json()
    assert snapshot["type"] == "session.snapshot"
    assert question["type"] == "jury.question"
    return snapshot, question


def submit(websocket, question_id: str, message_id: str | None = None) -> tuple[str, list[dict]]:
    identifier = message_id or str(uuid4())
    websocket.send_json(
        {
            "type": "answer.submit",
            "message_id": identifier,
            "payload": {
                "question_id": question_id,
                "content": "Respuesta sustentada con metodología, resultados y limitaciones.",
            },
        }
    )
    return identifier, [
        websocket.receive_json(),
        websocket.receive_json(),
        websocket.receive_json(),
    ]


def test_start_requires_ready_and_is_idempotent(client: TestClient, db_session: Session) -> None:
    document_id = ready_document(client, "session-start@example.com")
    simulation_id = create(client, document_id, profiles(client)[0]["id"]).json()["id"]
    assert client.post(f"/api/v1/simulations/{simulation_id}/start").status_code == 409
    assert (
        client.put(
            f"/api/v1/simulations/{simulation_id}/calibration",
            json={"camera_ready": True, "microphone_ready": True, "vision_ready": True},
        ).status_code
        == 200
    )

    first = start(client, simulation_id)
    second = start(client, simulation_id)
    assert first["status"] == "ACTIVE"
    assert first["turn_state"] == "WAITING_STUDENT"
    assert first["current_question"]["position"] == 1
    assert first["last_sequence"] == 1
    assert second["current_question"] == first["current_question"]
    assert second["started_at"] == first["started_at"]
    assert db_session.scalar(select(func.count()).select_from(SimulationTurn)) == 1


def test_session_snapshot_is_private_active_and_persisted(
    client: TestClient, db_session: Session
) -> None:
    simulation_id = ready_simulation(client, "session-owner@example.com")
    snapshot = start(client, simulation_id)
    db_session.expire_all()
    recovered = client.get(f"/api/v1/simulations/{simulation_id}/session")
    assert recovered.status_code == 200
    assert recovered.json() == snapshot

    register(client, "session-intruder@example.com")
    assert client.get(f"/api/v1/simulations/{simulation_id}/session").status_code == 404
    assert client.post(f"/api/v1/simulations/{simulation_id}/start").status_code == 404


def test_websocket_requires_cookie_allowed_origin_owner_and_active(client: TestClient) -> None:
    simulation_id = ready_simulation(client, "ws-policy@example.com")
    with pytest.raises(WebSocketDisconnect) as inactive:
        with client.websocket_connect(
            f"/api/v1/ws/simulations/{simulation_id}", headers={"origin": ALLOWED_ORIGIN}
        ):
            pass
    assert inactive.value.code == 4403
    start(client, simulation_id)

    with pytest.raises(WebSocketDisconnect) as bad_origin:
        with client.websocket_connect(
            f"/api/v1/ws/simulations/{simulation_id}", headers={"origin": "https://evil.test"}
        ):
            pass
    assert bad_origin.value.code == 4403

    client.cookies.clear()
    with pytest.raises(WebSocketDisconnect) as unauthenticated:
        with client.websocket_connect(
            f"/api/v1/ws/simulations/{simulation_id}", headers={"origin": ALLOWED_ORIGIN}
        ):
            pass
    assert unauthenticated.value.code == 4401


def test_websocket_answer_advances_and_reconnect_recovers_exact_question(
    client: TestClient, db_session: Session
) -> None:
    simulation_id = ready_simulation(client, "ws-reconnect@example.com")
    start(client, simulation_id)
    with client.websocket_connect(
        f"/api/v1/ws/simulations/{simulation_id}", headers={"origin": ALLOWED_ORIGIN}
    ) as websocket:
        snapshot, _ = receive_initial(websocket)
        first_question_id = snapshot["payload"]["current_question"]["id"]
        message_id, events = submit(websocket, first_question_id)
        assert [event["type"] for event in events] == [
            "answer.accepted",
            "session.state",
            "jury.question",
        ]
        assert events[0]["payload"]["duplicate"] is False
        assert events[1]["payload"]["answered_questions"] == 1
        assert events[2]["payload"]["position"] == 2
        websocket.send_json({"type": "heartbeat"})
        assert websocket.receive_json()["type"] == "heartbeat.ack"

    with client.websocket_connect(
        f"/api/v1/ws/simulations/{simulation_id}", headers={"origin": ALLOWED_ORIGIN}
    ) as websocket:
        snapshot, question = receive_initial(websocket)
        assert snapshot["payload"]["current_question"]["position"] == 2
        assert question["payload"]["position"] == 2
        _, replay = submit(websocket, first_question_id, message_id)
        assert replay[0]["type"] == "answer.accepted"
        assert replay[0]["payload"]["duplicate"] is True

    answers = db_session.scalar(
        select(func.count())
        .select_from(SimulationTurn)
        .where(
            SimulationTurn.simulation_id == simulation_id,
            SimulationTurn.turn_type == SimulationTurnType.ANSWER,
        )
    )
    assert answers == 1


def test_wrong_question_and_serialized_competing_answer_are_rejected(
    client: TestClient, db_session: Session
) -> None:
    simulation_id = ready_simulation(client, "ws-invalid-turn@example.com")
    start(client, simulation_id)
    with client.websocket_connect(
        f"/api/v1/ws/simulations/{simulation_id}", headers={"origin": ALLOWED_ORIGIN}
    ) as websocket:
        snapshot, _ = receive_initial(websocket)
        question_id = snapshot["payload"]["current_question"]["id"]
        websocket.send_json(
            {
                "type": "answer.submit",
                "message_id": str(uuid4()),
                "payload": {"question_id": str(uuid4()), "content": "Respuesta equivocada"},
            }
        )
        error = websocket.receive_json()
        assert error["type"] == "error" and error["code"] == "INVALID_TURN"
        _, accepted = submit(websocket, question_id)
        assert accepted[0]["type"] == "answer.accepted"
        competing_id = str(uuid4())
        websocket.send_json(
            {
                "type": "answer.submit",
                "message_id": competing_id,
                "payload": {"question_id": question_id, "content": "Segunda respuesta concurrente"},
            }
        )
        error = websocket.receive_json()
        assert error["code"] == "INVALID_TURN"

    question = db_session.get(SimulationQuestion, question_id)
    assert question is not None and question.status == SimulationQuestionStatus.ANSWERED
    assert (
        db_session.scalar(
            select(func.count())
            .select_from(SimulationTurn)
            .where(
                SimulationTurn.simulation_question_id == question_id,
                SimulationTurn.turn_type == SimulationTurnType.ANSWER,
            )
        )
        == 1
    )
    assert snapshot["payload"]["turn_state"] == SimulationTurnState.WAITING_STUDENT.value


@pytest.mark.parametrize("elapsed_minutes,expected_status", [(1, "ACTIVE"), (16, "COMPLETED")])
def test_answer_respects_elapsed_time_with_non_utc_database_timezone(
    client: TestClient, db_session: Session, elapsed_minutes: int, expected_status: str
) -> None:
    from app.modules.p1_gestion_identidad_seguridad.models.user import User
    from app.modules.p3_gestion_simulacion.models import Simulation
    from app.modules.p3_gestion_simulacion.services.session_service import SessionService

    simulation_id = ready_simulation(client, f"timezone-{elapsed_minutes}@example.com")
    initial = start(client, simulation_id)
    simulation = db_session.get(Simulation, simulation_id)
    simulation.started_at = (datetime.now(UTC) - timedelta(minutes=elapsed_minutes)).astimezone(
        timezone(timedelta(hours=-4))
    )
    db_session.commit()
    db_session.expire_all()
    owner = db_session.get(User, simulation.user_id)
    _, snapshot = SessionService(db_session).accept_answer(
        owner,
        simulation_id,
        message_id=str(uuid4()),
        question_id=initial["current_question"]["id"],
        content="La metodología se contrasta con la evidencia y sus limitaciones.",
    )
    assert snapshot.status == expected_status
    if expected_status == "ACTIVE":
        assert snapshot.current_question.position == 2
