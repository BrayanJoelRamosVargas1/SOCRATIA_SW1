"""Run the real P3-B persisted WebSocket session smoke against Docker."""

import json
import sys
import uuid

import httpx
from websockets.sync.client import connect

from scripts.smoke_cu10 import API_URL, build_document

WS_ORIGIN = "http://localhost:3000"


def create_ready_simulation(client: httpx.Client) -> str:
    suffix = uuid.uuid4().hex[:12]
    response = client.post(
        "/auth/register",
        json={
            "email": f"p3b-smoke-{suffix}@example.com",
            "full_name": "P3B Real Smoke",
            "password": f"Socratia session smoke {uuid.uuid4().hex}",
        },
    )
    response.raise_for_status()
    response = client.post(
        "/documents",
        files={
            "file": (
                "socratia-p3b-smoke.docx",
                build_document(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    response.raise_for_status()
    document_id = response.json()["id"]
    client.post(f"/documents/{document_id}/process").raise_for_status()
    client.post(f"/documents/{document_id}/questions/generate").raise_for_status()
    profiles = client.get("/jury-profiles")
    profiles.raise_for_status()
    response = client.post(
        "/simulations",
        json={
            "document_id": document_id,
            "jury_profile_id": profiles.json()[1]["id"],
            "planned_duration_minutes": 15,
        },
    )
    response.raise_for_status()
    simulation_id = response.json()["id"]
    response = client.put(
        f"/simulations/{simulation_id}/calibration",
        json={"camera_ready": True, "microphone_ready": True, "vision_ready": True},
    )
    response.raise_for_status()
    if response.json()["status"] != "READY":
        raise AssertionError("P3-B smoke could not prepare a READY simulation")
    return simulation_id


def receive(websocket) -> dict:
    return json.loads(websocket.recv())


def main() -> int:
    with httpx.Client(base_url=API_URL, timeout=300) as client:
        simulation_id = create_ready_simulation(client)
        response = client.post(f"/simulations/{simulation_id}/start")
        response.raise_for_status()
        started = response.json()
        if started["current_question"]["position"] != 1:
            raise AssertionError("P3-B did not persist the first jury question")

        cookie = "; ".join(f"{name}={value}" for name, value in client.cookies.items())
        websocket_url = f"ws://localhost:8000/api/v1/ws/simulations/{simulation_id}"
        last_message: dict | None = None
        with connect(
            websocket_url,
            origin=WS_ORIGIN,
            additional_headers={"Cookie": cookie},
        ) as websocket:
            snapshot_event = receive(websocket)
            question_event = receive(websocket)
            if snapshot_event["type"] != "session.snapshot":
                raise AssertionError("P3-B WebSocket did not send its persisted snapshot")
            if question_event["type"] != "jury.question":
                raise AssertionError("P3-B WebSocket did not send the current question")
            snapshot = snapshot_event["payload"]
            for expected_position in (2, 3, 4):
                question_id = snapshot["current_question"]["id"]
                last_message = {
                    "type": "answer.submit",
                    "message_id": str(uuid.uuid4()),
                    "payload": {
                        "question_id": question_id,
                        "content": (
                            "Respuesta de smoke sustentada con objetivos, metodología, "
                            "resultados y limitaciones."
                        ),
                    },
                }
                websocket.send(json.dumps(last_message))
                accepted = receive(websocket)
                state = receive(websocket)
                question = receive(websocket)
                if accepted["type"] != "answer.accepted" or accepted["payload"]["duplicate"]:
                    raise AssertionError("P3-B did not accept a unique answer")
                if state["type"] != "session.state" or question["type"] != "jury.question":
                    raise AssertionError("P3-B did not advance the persisted turn")
                snapshot = state["payload"]
                if snapshot["current_question"]["position"] != expected_position:
                    raise AssertionError("P3-B advanced to an unexpected question")

        if last_message is None:
            raise AssertionError("P3-B smoke did not submit answers")
        with connect(
            websocket_url,
            origin=WS_ORIGIN,
            additional_headers={"Cookie": cookie},
        ) as websocket:
            snapshot_event = receive(websocket)
            receive(websocket)
            if snapshot_event["payload"]["current_question"]["position"] != 4:
                raise AssertionError("P3-B reconnect did not recover question four")
            websocket.send(json.dumps(last_message))
            replay = receive(websocket)
            if replay["type"] != "answer.accepted" or not replay["payload"]["duplicate"]:
                raise AssertionError("P3-B idempotency did not recognize the retried message")
            receive(websocket)
            receive(websocket)

        persisted = client.get(f"/simulations/{simulation_id}/session")
        persisted.raise_for_status()
        final_snapshot = persisted.json()
        answers = [turn for turn in final_snapshot["transcript"] if turn["turn_type"] == "ANSWER"]
        if len(answers) != 3 or final_snapshot["answered_questions"] != 3:
            raise AssertionError("P3-B duplicated or lost an answer after reconnect")
        print(
            json.dumps(
                {
                    "simulation_id": simulation_id,
                    "status": final_snapshot["status"],
                    "turn_state": final_snapshot["turn_state"],
                    "answered_questions": final_snapshot["answered_questions"],
                    "current_question_position": final_snapshot["current_question"]["position"],
                    "answer_turns": len(answers),
                    "last_sequence": final_snapshot["last_sequence"],
                    "replayed_message_deduplicated": True,
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
