from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from fastapi import HTTPException
from app.integrations.tts.base import TTSRequest, TTSProviderError
from app.integrations.tts.local_tts import LocalTTSProvider
from app.modules.p3_gestion_simulacion.routes import simulation_routes as routes


@pytest.fixture
def speech(monkeypatch):
    question = SimpleNamespace(text="¿Cómo validó los resultados?",position=2)
    service = Mock()
    service.get_snapshot.return_value = SimpleNamespace(status="ACTIVE",current_question=question)
    monkeypatch.setattr(routes,"SessionService",lambda db:service)
    monkeypatch.setattr(routes,"get_settings",lambda:SimpleNamespace(local_tts_enabled=True,voice_tts_enabled=True))
    calls=[]
    async def synthesize(request):
        calls.append(request)
        yield b"RIFF-test"
    provider=SimpleNamespace(synthesize=synthesize,mime_type="audio/wav")
    monkeypatch.setattr(routes,"get_tts_provider",lambda:provider)
    return service, calls


@pytest.mark.asyncio
async def test_speech_uses_current_question_and_server_selected_speaker(speech):
    _,calls=speech
    result=await routes.jury_speech("id",routes.JurySpeechInput(text="¿Cómo validó los resultados?"),Mock(),Mock())
    assert result.media_type=="audio/wav"
    assert calls[0].speaker_index==1
    assert result.headers['cache-control']=='no-store'


@pytest.mark.asyncio
async def test_speech_rejects_arbitrary_text_before_synthesis(speech):
    _,calls=speech
    with pytest.raises(HTTPException) as error:
        await routes.jury_speech("id",routes.JurySpeechInput(text="Texto ajeno a la pregunta"),Mock(),Mock())
    assert error.value.status_code==422
    assert not calls


@pytest.mark.asyncio
async def test_owner_check_precedes_voice_work(speech):
    service,calls=speech
    service.get_snapshot.side_effect=HTTPException(403,"owner")
    with pytest.raises(HTTPException):
        await routes.jury_speech("other",routes.JurySpeechInput(text="¿Cómo validó los resultados?"),Mock(),Mock())
    assert not calls


@pytest.mark.asyncio
async def test_prewarm_uses_zero_based_bank_position(speech,monkeypatch):
    service,calls=speech
    service.get_snapshot.return_value.status="ACTIVE"
    question=SimpleNamespace(source="BANK",position=2,prompt_text=None,question=SimpleNamespace(question="Siguiente pregunta"))
    monkeypatch.setattr(routes,"TurnRepository",lambda db:SimpleNamespace(next_pending_question=lambda id:question))
    await routes.prewarm_jury_speech("id",Mock(),Mock())
    assert calls[0].text=="Siguiente pregunta"
    assert calls[0].speaker_index==2


def test_cpu_queue_is_bounded_and_busy_fails_without_loading_models():
    provider=LocalTTSProvider("missing-models")
    provider._lock.acquire()
    try:
        with pytest.raises(TTSProviderError) as error:
            provider._render(TTSRequest(text="Pregunta"))
        assert error.value.retryable
        assert provider._model is None
    finally:
        provider._lock.release()


@pytest.mark.parametrize("enabled,local,expected", [(True,True,True),(False,True,False),(True,False,False)])
def test_voice_capabilities_only_reports_enabled_audio(monkeypatch,enabled,local,expected):
    monkeypatch.setattr(routes,"get_settings",lambda:SimpleNamespace(voice_tts_enabled=enabled,local_tts_enabled=local))
    assert routes.voice_capabilities(Mock()) == {"local_audio":expected}


@pytest.mark.asyncio
async def test_short_intro_is_allowed_for_current_question(speech):
    _,calls=speech
    await routes.jury_speech("id",routes.JurySpeechInput(text="Bienvenido a tu defensa. Comencemos. ¿Cómo validó los resultados?"),Mock(),Mock())
    assert calls[0].speaker_index==1


def test_speech_segments_preserve_words_and_bound_normal_batches():
    from app.integrations.tts.local_tts import speech_segments
    text="¿Cómo validó los resultados de su investigación? "*10
    chunks=speech_segments(text)
    assert len(chunks)>1
    assert all(len(chunk)<=120 for chunk in chunks)
    assert " ".join(chunks)==" ".join(text.split())


@pytest.mark.asyncio
async def test_segment_request_cannot_escape_current_question(speech):
    service,calls=speech
    service.get_snapshot.return_value.current_question.text="Pregunta de investigación "*15
    body=routes.JurySpeechInput(text=service.get_snapshot.return_value.current_question.text,segment_index=0)
    response=await routes.jury_speech("id",body,Mock(),Mock())
    assert len(calls[0].text)<=120
    assert int(response.headers["x-speech-segments"])>1
    with pytest.raises(HTTPException) as error:
        await routes.jury_speech("id",body.model_copy(update={"segment_index":99}),Mock(),Mock())
    assert error.value.status_code==422
    assert len(calls)==1
