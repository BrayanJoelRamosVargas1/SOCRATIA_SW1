import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

load_dotenv(Path(__file__).parent.parent.parent / ".env")
if "DATABASE_URL" in os.environ and "TEST_DATABASE_URL" not in os.environ:
    os.environ["TEST_DATABASE_URL"] = os.environ["DATABASE_URL"]

from app.main import app
from tests.test_simulation_configuration import create, profiles, register

ALLOWED_ORIGIN = "http://localhost:3000"


def ready_simulation(client: TestClient, email: str, db: Session) -> str:
    from tests.test_simulation_configuration import document_bytes

    response = client.post(
        "/api/v1/documents",
        files={
            "file": (
                "mock-doc.docx",
                document_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 201
    document_id = response.json()["id"]

    client.post(f"/api/v1/documents/{document_id}/process").raise_for_status()

    from app.modules.p1_gestion_identidad_seguridad.models.user import User
    from app.modules.p2_gestion_documentos_preparacion.models.question_bank import (
        Question,
        QuestionBank,
        QuestionBankStatus,
    )

    user_id = db.query(User).filter_by(email=email).first().id
    bank = QuestionBank(document_id=document_id, user_id=user_id, status=QuestionBankStatus.READY)
    db.add(bank)
    db.commit()

    for i in range(12):
        q = Question(
            question_bank_id=bank.id,
            question=f"Pregunta de prueba {i + 1}?",
            expected_answer_points=["punto 1", "punto 2"],
            category="TECHNICAL",
            difficulty="MEDIUM",
            source_chunk_ids=[],
            position=i,
        )
        db.add(q)
    db.commit()

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


def test_p3c_voice_integration_real_credentials(db_session: Session):
    client = TestClient(app)
    email = f"p3c-real-{uuid.uuid4().hex[:6]}@example.com"
    register(client, email)
    sim_id = ready_simulation(client, email, db_session)
    start(client, sim_id)

    with client.websocket_connect(
        f"/api/v1/ws/simulations/{sim_id}", headers={"origin": ALLOWED_ORIGIN}
    ) as websocket:
        snapshot = websocket.receive_json()
        assert snapshot["type"] == "session.snapshot"
        q1 = websocket.receive_json()
        assert q1["type"] == "jury.question"

        websocket.send_bytes(b"audio without start")
        err = websocket.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "NO_ACTIVE_UTTERANCE"

        large_id = str(uuid.uuid4())
        websocket.send_json(
            {
                "type": "voice.utterance.start",
                "message_id": large_id,
                "payload": {"mime_type": "audio/webm"},
            }
        )
        assert websocket.receive_json()["type"] == "voice.listening"
        max_size = 5 * 1024 * 1024
        websocket.send_bytes(b"0" * (max_size + 10))
        err2 = websocket.receive_json()
        assert err2["code"] == "UTTERANCE_TOO_LARGE"

        mime_id = str(uuid.uuid4())
        websocket.send_json(
            {
                "type": "voice.utterance.start",
                "message_id": mime_id,
                "payload": {"mime_type": "video/mp4"},
            }
        )
        err3 = websocket.receive_json()
        assert err3["code"] == "INVALID_MIME_TYPE"

        msg_id = str(uuid.uuid4())
        websocket.send_json(
            {
                "type": "voice.utterance.start",
                "message_id": msg_id,
                "payload": {"mime_type": "audio/mpeg"},
            }
        )
        assert websocket.receive_json()["type"] == "voice.listening"

        fixture_path = Path(__file__).parent / "fixtures" / "hola.mp3"
        with fixture_path.open("rb") as f:
            websocket.send_bytes(f.read())

        websocket.send_json({"type": "voice.utterance.end", "message_id": msg_id})
        assert websocket.receive_json()["type"] == "voice.transcribing"

        transcription = websocket.receive_json()
        assert transcription["type"] == "voice.transcription"
        assert len(transcription["text"]) > 0

        state = websocket.receive_json()
        assert state["type"] == "session.state"

        q2 = websocket.receive_json()
        assert q2["type"] == "jury.question"

        assert websocket.receive_json()["type"] == "jury.speaking"
        assert websocket.receive_json()["type"] == "tts.started"

        audio_bytes = 0
        is_fallback = False
        while True:
            msg = websocket.receive()
            if "bytes" in msg:
                audio_bytes += len(msg["bytes"])
            elif "text" in msg:
                d = json.loads(msg["text"])
                if d["type"] == "tts.fallback":
                    is_fallback = True
                    break
                if d["type"] == "tts.completed":
                    break

        if not is_fallback:
            assert audio_bytes > 0
        assert websocket.receive_json()["type"] == "jury.finished"

        sil_id = str(uuid.uuid4())
        websocket.send_json(
            {
                "type": "voice.utterance.start",
                "message_id": sil_id,
                "payload": {"mime_type": "audio/mpeg"},
            }
        )
        assert websocket.receive_json()["type"] == "voice.listening"
        websocket.send_bytes(b"\x00\x00")
        websocket.send_json({"type": "voice.utterance.end", "message_id": sil_id})
        assert websocket.receive_json()["type"] == "voice.transcribing"

        t_sil = websocket.receive_json()
        if t_sil["type"] == "stt.degraded":
            curr_q_id = q2["payload"]["id"]
        else:
            assert t_sil["type"] == "voice.transcription"
            assert t_sil["text"].strip() == ""

            assert websocket.receive_json()["type"] == "session.state"
            q_sil = websocket.receive_json()
            assert q_sil["type"] == "jury.question"

            fb = websocket.receive_json()
            assert fb["type"] == "tts.fallback"
            curr_q_id = q_sil["payload"]["id"]

        for _ in range(12):
            text_id = str(uuid.uuid4())
            websocket.send_json(
                {
                    "type": "answer.submit",
                    "message_id": text_id,
                    "payload": {"question_id": curr_q_id, "content": "Respuesta"},
                }
            )
            resp = websocket.receive_json()
            if resp["type"] == "error" and resp["code"] == "SESSION_QUESTIONS_EXHAUSTED":
                break
            if resp["type"] == "answer.accepted":
                state = websocket.receive_json()
                if state["payload"].get("questions_exhausted"):
                    break
                q_next = websocket.receive_json()
                curr_q_id = q_next["payload"]["id"]

        websocket.send_json(
            {
                "type": "voice.utterance.start",
                "message_id": str(uuid.uuid4()),
                "payload": {"mime_type": "audio/mpeg"},
            }
        )
        err12 = websocket.receive_json()
        assert err12["type"] == "error"
        assert err12["code"] == "SESSION_QUESTIONS_EXHAUSTED"
