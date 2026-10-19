from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from test_simulation_sessions import ready_simulation, start

from app.integrations.llm.jury_base import JuryAction
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p3_gestion_simulacion.models import Simulation, SimulationTurn, SimulationTurnType
from app.modules.p3_gestion_simulacion.models.voice_utterance import VoiceUtterance
from app.modules.p3_gestion_simulacion.services import voice_service as module


@pytest.fixture
def voice_session(client, db_session, monkeypatch):
    simulation_id = ready_simulation(client, 'voice-flow@example.com')
    start(client, simulation_id)
    simulation = db_session.get(Simulation, simulation_id)
    owner = db_session.get(User, simulation.user_id)
    stt = SimpleNamespace(primary=SimpleNamespace(name='fixture'),
        transcribe=AsyncMock(return_value=('La evidencia respalda los resultados.', False, 12)))
    router = SimpleNamespace(route=AsyncMock(return_value=SimpleNamespace(decision=SimpleNamespace(
        action=JuryAction.NEXT_BANK, follow_up_question=None))))
    tts = Mock()
    monkeypatch.setattr(module, 'get_stt_router', lambda: stt)
    monkeypatch.setattr(module, 'get_jury_routing_router', lambda **_: router)
    monkeypatch.setattr(module, 'get_tts_provider', lambda: tts)
    return module.VoiceService(db_session, owner, simulation_id), simulation, stt, router, tts


@pytest.mark.asyncio
async def test_voice_replay_does_not_transcribe_route_or_advance_twice(voice_session, db_session):
    service, simulation, stt, router, tts = voice_session
    message_id = str(uuid4())
    first = await service.process_utterance(message_id, 'audio/webm', b'fixture audio')
    replay = await service.process_utterance(message_id, 'audio/webm', b'fixture audio')
    assert first[4].answered_questions == replay[4].answered_questions == 1
    assert first[4].current_question.id == replay[4].current_question.id
    assert replay[2] is None and replay[3] is None
    stt.transcribe.assert_awaited_once()
    router.route.assert_awaited_once()
    tts.synthesize.assert_called_once()
    assert db_session.scalar(select(func.count()).select_from(VoiceUtterance)) == 1
    assert db_session.scalar(select(func.count()).select_from(SimulationTurn).where(
        SimulationTurn.simulation_id == simulation.id, SimulationTurn.turn_type == SimulationTurnType.ANSWER)) == 1


@pytest.mark.asyncio
async def test_voice_at_time_limit_closes_without_llm_or_tts(voice_session, db_session):
    service, simulation, stt, router, tts = voice_session
    simulation.started_at = datetime.now(UTC) - timedelta(minutes=simulation.planned_duration_minutes + 1)
    db_session.commit()
    result = await service.process_utterance(str(uuid4()), 'audio/webm', b'fixture audio')
    assert result[4].status == 'COMPLETED'
    assert result[2] is None and result[3] is None
    stt.transcribe.assert_awaited_once()
    router.route.assert_not_called()
    tts.synthesize.assert_not_called()


@pytest.mark.asyncio
async def test_silence_does_not_persist_an_answer_or_transcript(voice_session, db_session):
    service, _, stt, router, tts = voice_session
    stt.transcribe.return_value = ('  ', False, 12)
    result = await service.process_utterance(str(uuid4()), 'audio/webm', b'silent fixture')
    assert result[4].answered_questions == 0
    assert db_session.scalar(select(func.count()).select_from(VoiceUtterance)) == 0
    router.route.assert_not_called()
    tts.synthesize.assert_not_called()


@pytest.mark.asyncio
async def test_unavailable_jury_provider_still_advances_to_bank_question(voice_session, monkeypatch):
    service, _, _, _, _ = voice_session
    monkeypatch.setattr(module, 'get_jury_routing_router', Mock(side_effect=RuntimeError('fixture unavailable')))
    result = await service.process_utterance(str(uuid4()), 'audio/webm', b'fixture audio')
    assert result[4].answered_questions == 1
    assert result[4].current_question.position == 2
    assert result[2] == JuryAction.NEXT_BANK.value


@pytest.mark.asyncio
async def test_unavailable_tts_returns_question_for_browser_fallback(voice_session, monkeypatch):
    service, _, _, _, _ = voice_session
    monkeypatch.setattr(module, 'get_tts_provider', Mock(side_effect=RuntimeError('fixture unavailable')))
    result = await service.process_utterance(str(uuid4()), 'audio/webm', b'fixture audio')
    assert result[4].answered_questions == 1
    assert result[4].current_question.position == 2
    assert result[3] is None


@pytest.mark.asyncio
async def test_local_batch_voice_does_not_duplicate_websocket_synthesis(voice_session, monkeypatch):
    service, _, _, _, tts = voice_session
    monkeypatch.setattr(module, 'get_settings', lambda: SimpleNamespace(local_tts_enabled=True))
    result = await service.process_utterance(str(uuid4()), 'audio/webm', b'fixture audio')
    assert result[4].current_question.position == 2
    assert result[3] is None
    tts.synthesize.assert_not_called()
