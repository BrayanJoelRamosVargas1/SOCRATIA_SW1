import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import DomainError
from app.core.security import decode_access_token
from app.core.websocket import SimulationConnectionManager
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p1_gestion_identidad_seguridad.repositories.user_repository import (
    UserRepository,
)
from app.modules.p3_gestion_simulacion.schemas.session import (
    AnswerSubmitMessage,
    ServerEventState,
    SessionSnapshot,
    VoiceUtteranceEndMessage,
    VoiceUtteranceStartMessage,
)
from app.modules.p3_gestion_simulacion.services.session_service import SessionService
from app.modules.p3_gestion_simulacion.services.voice_service import VoiceService

router = APIRouter()
manager = SimulationConnectionManager()
logger = logging.getLogger(__name__)
Database = Annotated[Session, Depends(get_db)]


def _authenticated_user(websocket: WebSocket, db: Session) -> User | None:
    settings = get_settings()
    token = websocket.cookies.get(settings.access_cookie_name)
    if token is None:
        return None
    try:
        claims = decode_access_token(token)
    except ValueError:
        return None
    user = UserRepository(db).get_by_id(claims.user_id)
    if user is None or not user.is_active or user.auth_version != claims.auth_version:
        return None
    return user


async def _send_snapshot(websocket: WebSocket, snapshot: SessionSnapshot) -> None:
    await websocket.send_json(
        {"type": "session.snapshot", "payload": snapshot.model_dump(mode="json")}
    )
    if snapshot.current_question is not None:
        await websocket.send_json(
            {
                "type": "jury.question",
                "sequence": snapshot.last_sequence,
                "payload": snapshot.current_question.model_dump(mode="json"),
            }
        )


@router.websocket("/ws/simulations/{simulation_id}")
async def simulation_session(
    websocket: WebSocket,
    simulation_id: str,
    db: Database,
) -> None:
    settings = get_settings()
    if websocket.headers.get("origin") not in settings.cors_origin_list:
        await websocket.close(code=4403, reason="Origin not allowed")
        return
    user = _authenticated_user(websocket, db)
    if user is None:
        await websocket.close(code=4401, reason="Authentication required")
        return
    try:
        snapshot = SessionService(db).get_snapshot(user, simulation_id)
    except DomainError:
        db.rollback()
        await websocket.close(code=4403, reason="Session unavailable")
        return

    await manager.connect(simulation_id, websocket)
    logger.info("WS_CONNECTED simulation_id=%s user_id=%s", simulation_id, user.id)
    await _send_snapshot(websocket, snapshot)

    current_utterance_id: str | None = None
    current_mime_type: str | None = None
    audio_buffer = bytearray()

    try:
        while True:
            # We can receive json or bytes
            message = await websocket.receive()
            if "bytes" in message:
                if current_utterance_id:
                    audio_buffer.extend(message["bytes"])
                continue

            if "text" not in message:
                continue

            import json

            try:
                msg_data = json.loads(message["text"])
            except json.JSONDecodeError:
                continue

            if msg_data.get("type") == "heartbeat":
                await websocket.send_json(
                    {
                        "type": "heartbeat.ack",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                )
                continue
            try:
                submitted = AnswerSubmitMessage.model_validate(msg_data)
                accepted, snapshot = SessionService(db).accept_answer(
                    user,
                    simulation_id,
                    message_id=str(submitted.message_id),
                    question_id=submitted.payload.question_id,
                    content=submitted.payload.content,
                )
                await websocket.send_json(
                    {"type": "answer.accepted", "payload": accepted.model_dump(mode="json")}
                )
                await websocket.send_json(
                    {
                        "type": "session.state",
                        "payload": snapshot.model_dump(mode="json"),
                    }
                )
                if snapshot.current_question is not None:
                    await websocket.send_json(
                        {
                            "type": "jury.question",
                            "sequence": snapshot.last_sequence,
                            "payload": snapshot.current_question.model_dump(mode="json"),
                        }
                    )

            except ValidationError:
                # Could be voice.utterance.start
                try:
                    start_msg = VoiceUtteranceStartMessage.model_validate(msg_data)
                    current_utterance_id = str(start_msg.message_id)
                    current_mime_type = start_msg.payload.mime_type
                    audio_buffer.clear()
                    await websocket.send_json(
                        ServerEventState(type="voice.listening").model_dump(mode="json")
                    )
                    continue
                except ValidationError:
                    pass

                try:
                    end_msg = VoiceUtteranceEndMessage.model_validate(msg_data)
                    if str(end_msg.message_id) == current_utterance_id:
                        await websocket.send_json(
                            ServerEventState(type="voice.transcribing").model_dump(mode="json")
                        )

                        # Process audio
                        try:
                            voice_svc = VoiceService(db, user, simulation_id)
                            (
                                text,
                                fallback,
                                action,
                                tts_stream,
                                snapshot,
                            ) = await voice_svc.process_utterance(
                                message_id=current_utterance_id,
                                mime_type=current_mime_type or "audio/webm",
                                audio_bytes=bytes(audio_buffer),
                            )

                            # Send text to client as if it were typed
                            await websocket.send_json(
                                {
                                    "type": "voice.transcription",
                                    "message_id": current_utterance_id,
                                    "text": text,
                                }
                            )

                            await websocket.send_json(
                                {
                                    "type": "session.state",
                                    "payload": snapshot.model_dump(mode="json"),
                                }
                            )

                            if snapshot.current_question is not None:
                                await websocket.send_json(
                                    {
                                        "type": "jury.question",
                                        "sequence": snapshot.last_sequence,
                                        "payload": snapshot.current_question.model_dump(
                                            mode="json"
                                        ),
                                    }
                                )

                            if tts_stream:
                                await websocket.send_json(
                                    ServerEventState(type="jury.speaking").model_dump(mode="json")
                                )
                                async for chunk in tts_stream:
                                    await websocket.send_bytes(chunk)
                                await websocket.send_json(
                                    ServerEventState(type="jury.finished").model_dump(mode="json")
                                )

                        except Exception as e:
                            logger.error("Voice processing error: %s", str(e))
                            await websocket.send_json(
                                ServerEventState(
                                    type="error", message="Error procesando voz."
                                ).model_dump(mode="json")
                            )

                        current_utterance_id = None
                        current_mime_type = None
                        audio_buffer.clear()
                    continue
                except ValidationError:
                    pass

                await websocket.send_json(
                    {
                        "type": "error",
                        "code": "INVALID_MESSAGE",
                        "message": "El mensaje no cumple el protocolo de la sesión.",
                    }
                )
            except DomainError as exc:
                db.rollback()
                await websocket.send_json(
                    {
                        "type": "error",
                        "code": exc.code.upper(),
                        "message": exc.message,
                        "message_id": msg_data.get("message_id")
                        if isinstance(msg_data, dict)
                        else None,
                    }
                )
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await manager.disconnect(simulation_id, websocket)
        logger.info("WS_DISCONNECTED simulation_id=%s user_id=%s", simulation_id, user.id)
