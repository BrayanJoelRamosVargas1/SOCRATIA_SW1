import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.modules.p3_gestion_simulacion.routes import session_websocket as route


@pytest.mark.asyncio
async def test_cancel_discards_audio_without_processing_or_advancing_session(monkeypatch):
    utterance_id = str(uuid4())
    events = iter([
        {"text": json.dumps({"type": "voice.utterance.start", "message_id": utterance_id, "payload": {"mime_type": "audio/webm"}})},
        {"bytes": b"discarded audio"},
        {"text": json.dumps({"type": "voice.utterance.cancel", "message_id": str(uuid4())})},
        {"bytes": b"still active after wrong cancel"},
        {"text": json.dumps(["invalid", "message"])},
        {"text": json.dumps({"type": "voice.utterance.cancel", "message_id": utterance_id})},
        {"bytes": b"late audio"},
        {"type": "websocket.disconnect", "code": 1000},
    ])
    websocket = SimpleNamespace(headers={"origin": "http://localhost:3000"}, receive=AsyncMock(side_effect=lambda: next(events)), send_json=AsyncMock())
    snapshot = SimpleNamespace(last_sequence=1, current_question=SimpleNamespace(model_dump=lambda **_: {}), questions_exhausted=False, model_dump=lambda **_: {})
    service = Mock()
    service.get_snapshot.return_value = snapshot
    voice = Mock()
    manager = SimpleNamespace(connect=AsyncMock(), disconnect=AsyncMock())
    monkeypatch.setattr(route, "get_settings", lambda: SimpleNamespace(cors_origin_list=["http://localhost:3000"], voice_max_utterance_bytes=1000))
    monkeypatch.setattr(route, "_authenticated_user", lambda *_: SimpleNamespace(id="student"))
    monkeypatch.setattr(route, "SessionService", lambda _: service)
    monkeypatch.setattr(route, "VoiceService", voice)
    monkeypatch.setattr(route, "manager", manager)
    await route.simulation_session(websocket, "simulation", Mock())
    messages = [call.args[0] for call in websocket.send_json.call_args_list]
    assert sum(message["type"] == "voice.cancelled" for message in messages) == 1
    assert sum(message.get("code") == "NO_ACTIVE_UTTERANCE" for message in messages) == 1
    voice.assert_not_called()
    service.accept_answer.assert_not_called()
    manager.disconnect.assert_awaited_once()
