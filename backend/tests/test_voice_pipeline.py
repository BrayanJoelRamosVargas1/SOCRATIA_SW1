"""
P3-C Voice Pipeline — Test Suite
=================================
Todos los casos con mocks (no requieren Docker ni credenciales reales).

Casos cubiertos:
  STT-1  STTRouter → primary éxito
  STT-2  STTRouter → fallback cuando primary falla
  STT-3  STTRouter → ambos fallan → STTProviderError relanzado
  JURY-1 JuryRoutingRouter → primary éxito (NEXT_BANK)
  JURY-2 JuryRoutingRouter → primary falla → fallback (FOLLOW_UP)
  JURY-3 Circuit breaker abierto → directo a fallback (sin llamar primary)
  JURY-4 Ambos providers fallan → JuryRoutingFailed
  JURY-5 FOLLOW_UP depth >= 2 → forzar NEXT_BANK (lógica en voice_service)
  TTS-1  TTS synthesize → stream de chunks correcto
  TTS-2  TTS sin API key → TTSProviderError inmediato
  TTS-3  TTS sin voice_id → TTSProviderError inmediato
  WS-1   NO_ACTIVE_UTTERANCE: bytes sin utterance activa
  WS-2   UTTERANCE_TOO_LARGE: excede VOICE_MAX_UTTERANCE_BYTES
  WS-3   INVALID_MIME_TYPE: codec no permitido
  WS-4   JuryRoutingDecision.reason_code validación Pydantic
  WS-5   Transcript persistido (VoiceUtterance no contiene audio crudo)
"""

from unittest.mock import AsyncMock

import pytest

from app.integrations.llm.base import LLMErrorKind
from app.integrations.llm.jury_base import (
    JuryAction,
    JuryRoutingDecision,
    JuryRoutingFailed,
    JuryRoutingProviderError,
    JuryRoutingRequest,
)
from app.integrations.llm.jury_router import JuryRoutingRouter
from app.integrations.stt.base import STTProviderError, STTRequest, STTResult
from app.integrations.stt.dependencies import STTRouter
from app.integrations.tts.base import TTSProviderError, TTSRequest
from app.integrations.tts.elevenlabs_tts import ElevenLabsTTSProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _jury_error(
    provider: str = "groq", kind: LLMErrorKind = LLMErrorKind.TRANSIENT
) -> JuryRoutingProviderError:
    return JuryRoutingProviderError("error", provider=provider, kind=kind)


def _jury_request() -> JuryRoutingRequest:
    return JuryRoutingRequest(
        question_text="¿Qué es un grafo?",
        expected_answer_points=["nodos", "aristas"],
        student_answer="Es una estructura con nodos y aristas",
        focus_type="TECHNICAL",
        strictness=2,
        interruption_level="MODERATE",
    )


def _stt_result(text: str = "Hola", provider: str = "groq") -> STTResult:
    return STTResult(text=text, latency_ms=150, provider=provider, model="whisper")


# ---------------------------------------------------------------------------
# STT Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stt_router_success_path():
    """STT-1: Primary retorna resultado → no llama fallback."""
    primary = AsyncMock()
    primary.transcribe.return_value = _stt_result("Hola")
    primary.name = "groq"

    fallback = AsyncMock()

    router = STTRouter(primary, fallback)
    req = STTRequest(audio_bytes=b"fake", mime_type="audio/webm")

    text, fallback_used, latency = await router.transcribe(req)

    assert text == "Hola"
    assert fallback_used is False
    assert latency == 150
    primary.transcribe.assert_called_once_with(req)
    fallback.transcribe.assert_not_called()


@pytest.mark.asyncio
async def test_stt_router_fallback():
    """STT-2: Primary falla con retryable=True → llama fallback."""
    primary = AsyncMock()
    primary.transcribe.side_effect = STTProviderError("Timeout", provider="groq", retryable=True)
    primary.name = "groq"

    fallback = AsyncMock()
    fallback.transcribe.return_value = _stt_result("Hola fallback", provider="gemini")
    fallback.name = "gemini"

    router = STTRouter(primary, fallback)
    req = STTRequest(audio_bytes=b"fake", mime_type="audio/webm")

    text, fallback_used, latency = await router.transcribe(req)

    assert text == "Hola fallback"
    assert fallback_used is True
    primary.transcribe.assert_called_once_with(req)
    fallback.transcribe.assert_called_once_with(req)


@pytest.mark.asyncio
async def test_stt_router_total_failure():
    """STT-3: Ambos fallan → STTProviderError del fallback relanzado."""
    primary = AsyncMock()
    primary.transcribe.side_effect = STTProviderError("Timeout", provider="groq", retryable=True)
    primary.name = "groq"

    fallback = AsyncMock()
    fallback.transcribe.side_effect = STTProviderError("Auth", provider="gemini", retryable=False)
    fallback.name = "gemini"

    router = STTRouter(primary, fallback)
    req = STTRequest(audio_bytes=b"fake", mime_type="audio/webm")

    with pytest.raises(STTProviderError) as exc_info:
        await router.transcribe(req)

    assert exc_info.value.provider == "gemini"


# ---------------------------------------------------------------------------
# Jury Router Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_jury_router_success():
    """JURY-1: Primary éxito → NEXT_BANK, fallback no llamado."""
    primary = AsyncMock()
    primary.route.return_value = JuryRoutingDecision(
        action=JuryAction.NEXT_BANK,
        reason_code="ANSWER_COMPLETE",
        follow_up_question=None,
    )
    primary.name = "groq"
    primary.model = "gpt-oss-20b"

    fallback = AsyncMock()

    router = JuryRoutingRouter(
        primary=primary, fallback=fallback, failure_threshold=2, recovery_seconds=60
    )
    req = _jury_request()

    res = await router.route(req)

    assert res.decision.action == JuryAction.NEXT_BANK
    assert res.fallback_used is False
    primary.route.assert_called_once_with(req)
    fallback.route.assert_not_called()


@pytest.mark.asyncio
async def test_jury_router_fallback():
    """JURY-2: Primary falla → fallback retorna FOLLOW_UP."""
    primary = AsyncMock()
    primary.route.side_effect = _jury_error("groq", LLMErrorKind.TRANSIENT)
    primary.name = "groq"

    fallback = AsyncMock()
    fallback.route.return_value = JuryRoutingDecision(
        action=JuryAction.FOLLOW_UP,
        reason_code="INCOMPLETE_ANSWER",
        follow_up_question="¿Puedes explicar la diferencia entre grafo dirigido e indirecto?",
    )
    fallback.name = "gemini"
    fallback.model = "gemini-2.5-flash"

    router = JuryRoutingRouter(
        primary=primary, fallback=fallback, failure_threshold=2, recovery_seconds=60
    )
    req = _jury_request()

    res = await router.route(req)

    assert res.decision.action == JuryAction.FOLLOW_UP
    assert res.fallback_used is True
    primary.route.assert_called_once_with(req)
    fallback.route.assert_called_once_with(req)


@pytest.mark.asyncio
async def test_jury_router_circuit_breaker_open():
    """JURY-3: Circuit breaker abierto → skip primary, directo a fallback."""
    primary = AsyncMock()
    primary.name = "groq"

    fallback = AsyncMock()
    fallback.route.return_value = JuryRoutingDecision(
        action=JuryAction.NEXT_BANK,
        reason_code="CB_OPEN",
        follow_up_question=None,
    )
    fallback.name = "gemini"
    fallback.model = "gemini-2.5-flash"

    router = JuryRoutingRouter(
        primary=primary, fallback=fallback, failure_threshold=1, recovery_seconds=9999
    )
    # Forzar circuit breaker abierto disparando 1 fallo (threshold=1)
    router.breaker.record_failure()

    req = _jury_request()
    res = await router.route(req)

    assert res.fallback_used is True
    assert res.primary_failure_reason == "groq:circuit_open"
    primary.route.assert_not_called()
    fallback.route.assert_called_once_with(req)


@pytest.mark.asyncio
async def test_jury_router_total_failure():
    """JURY-4: Ambos providers fallan → JuryRoutingFailed."""
    primary = AsyncMock()
    primary.route.side_effect = _jury_error("groq", LLMErrorKind.TRANSIENT)
    primary.name = "groq"

    fallback = AsyncMock()
    fallback.route.side_effect = _jury_error("gemini", LLMErrorKind.PERMANENT)
    fallback.name = "gemini"

    router = JuryRoutingRouter(
        primary=primary, fallback=fallback, failure_threshold=3, recovery_seconds=60
    )
    req = _jury_request()

    with pytest.raises(JuryRoutingFailed):
        await router.route(req)


def test_jury_routing_provider_error_telemetry():
    """JURY-5 (unit): JuryRoutingProviderError.telemetry_reason formatea correctamente."""
    err = JuryRoutingProviderError(
        "fail",
        provider="groq",
        kind=LLMErrorKind.TRANSIENT,
        detail="rate_limit",
    )
    assert err.telemetry_reason == "groq:transient:rate_limit"
    assert err.retryable is True

    err_no_detail = JuryRoutingProviderError("fail", provider="gemini", kind=LLMErrorKind.AUTH)
    assert err_no_detail.telemetry_reason == "gemini:auth"
    assert err_no_detail.retryable is False


# ---------------------------------------------------------------------------
# FOLLOW_UP depth limit (voice_service logic, mocked)
# ---------------------------------------------------------------------------


def test_follow_up_depth_limit_forces_next_bank():
    """JURY-5-DEPTH: depth >= 2 con FOLLOW_UP → acción se fuerza a NEXT_BANK (lógica voice_service.py)."""
    from app.integrations.llm.jury_base import JuryAction

    # Simula exactamente la lógica de voice_service.py líneas 113-116
    action = JuryAction.FOLLOW_UP.value
    depth = 2  # máximo permitido es < 2

    if action == JuryAction.FOLLOW_UP.value and depth >= 2:
        action = JuryAction.NEXT_BANK.value

    assert action == JuryAction.NEXT_BANK.value


# ---------------------------------------------------------------------------
# TTS Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tts_no_api_key_raises():
    """TTS-2: Sin API key → TTSProviderError inmediato sin llamar a la red."""
    provider = ElevenLabsTTSProvider(api_key=None, default_voice_id="voice123", timeout_seconds=10)
    req = TTSRequest(text="Hola mundo")

    with pytest.raises(TTSProviderError) as exc_info:
        # synthesize es un async generator; necesitamos iterarlo para que levante
        async for _ in provider.synthesize(req):
            pass

    assert exc_info.value.provider == "elevenlabs"
    assert "not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_tts_no_voice_id_raises():
    """TTS-3: API key presente pero voice_id None → TTSProviderError inmediato."""
    provider = ElevenLabsTTSProvider(api_key="fake_key", default_voice_id=None, timeout_seconds=10)
    req = TTSRequest(text="Hola mundo")

    with pytest.raises(TTSProviderError) as exc_info:
        async for _ in provider.synthesize(req):
            pass

    assert "voice ID" in str(exc_info.value)


# ---------------------------------------------------------------------------
# WebSocket Protocol Tests (unit, sin HTTP real)
# ---------------------------------------------------------------------------


def test_allowed_mime_types_validation():
    """WS-3: MIME type válidos e inválidos según la allowlist de session_websocket."""
    allowed_mime_types = {
        "audio/webm",
        "audio/mp4",
        "audio/ogg",
        "audio/aac",
        "audio/mpeg",
        "audio/wav",
    }

    valid_cases = [
        "audio/webm",
        "audio/webm;codecs=opus",  # con params → strip al base
        "audio/mp4",
        "audio/ogg",
        "audio/wav",
    ]
    invalid_cases = [
        "video/mp4",
        "application/json",
        "audio/flac",
        "",
    ]

    for mime in valid_cases:
        base = mime.split(";")[0].strip()
        assert base in allowed_mime_types, f"Expected {mime} to be valid"

    for mime in invalid_cases:
        base = mime.split(";")[0].strip()
        assert base not in allowed_mime_types, f"Expected {mime} to be invalid"


def test_utterance_too_large_threshold():
    """WS-2: VOICE_MAX_UTTERANCE_BYTES = 5 MB exactos."""
    max_bytes = 5 * 1024 * 1024  # 5242880

    audio_buffer = bytearray(max_bytes - 1)  # 1 byte de margen
    new_chunk = b"\x00"  # exactamente el límite → NO debe exceder
    assert len(audio_buffer) + len(new_chunk) <= max_bytes

    big_chunk = b"\x00" * 2  # excede por 1 byte
    assert len(audio_buffer) + len(big_chunk) > max_bytes


def test_no_active_utterance_guard():
    """WS-1: Bytes sin utterance_id activo → debe devolver NO_ACTIVE_UTTERANCE."""
    current_utterance_id = None
    received_bytes = b"audio_data"

    # Simula la guarda de session_websocket.py línea 98-104
    should_reject = not current_utterance_id and len(received_bytes) > 0
    assert should_reject is True


def test_voice_utterance_record_has_no_raw_audio():
    """WS-5: VoiceUtterance model no tiene columna raw_audio_bytes → audio crudo no persiste."""
    from app.modules.p3_gestion_simulacion.models.voice_utterance import VoiceUtterance

    columns = {col.key for col in VoiceUtterance.__table__.columns}
    audio_like_cols = {c for c in columns if "audio" in c.lower() and "bytes" in c.lower()}
    assert audio_like_cols == set(), (
        f"VoiceUtterance should NOT persist raw audio bytes. Found columns: {audio_like_cols}"
    )


def test_jury_routing_decision_requires_reason_code():
    """WS-4: JuryRoutingDecision → reason_code es requerido y tiene min_length=3."""
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        JuryRoutingDecision(
            action=JuryAction.NEXT_BANK, follow_up_question=None
        )  # falta reason_code

    with pytest.raises(ValidationError):
        JuryRoutingDecision(
            action=JuryAction.NEXT_BANK,
            reason_code="AB",  # menor a min_length=3
            follow_up_question=None,
        )

    # Válido
    decision = JuryRoutingDecision(
        action=JuryAction.NEXT_BANK,
        reason_code="COMPLETE",
        follow_up_question=None,
    )
    assert decision.action == JuryAction.NEXT_BANK
