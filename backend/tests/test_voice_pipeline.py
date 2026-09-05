from unittest.mock import AsyncMock

import pytest

from app.integrations.llm.jury_base import (
    JuryAction,
    JuryRoutingDecision,
    JuryRoutingProviderError,
    JuryRoutingRequest,
)
from app.integrations.llm.jury_router import JuryRoutingRouter
from app.integrations.stt.base import STTProviderError, STTRequest
from app.integrations.stt.dependencies import STTRouter


@pytest.mark.asyncio
async def test_stt_router_success_path():
    primary = AsyncMock()
    primary.transcribe.return_value = "Hola"
    primary.name = "groq"
    
    fallback = AsyncMock()
    
    router = STTRouter(primary, fallback)
    req = STTRequest(audio_bytes=b"fake", mime_type="audio/webm")
    
    text, fallback_used, latency = await router.transcribe(req)
    
    assert text == "Hola"
    assert fallback_used is False
    primary.transcribe.assert_called_once_with(req)
    fallback.transcribe.assert_not_called()

@pytest.mark.asyncio
async def test_stt_router_fallback():
    primary = AsyncMock()
    primary.transcribe.side_effect = STTProviderError("Timeout", provider="groq", retryable=True)
    primary.name = "groq"
    
    fallback = AsyncMock()
    fallback.transcribe.return_value = "Hola fallback"
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

@pytest.mark.asyncio
async def test_jury_router_success():
    primary = AsyncMock()
    primary.route.return_value = JuryRoutingDecision(action=JuryAction.NEXT_BANK, follow_up_question=None)
    primary.name = "groq"
    primary.model = "groq"
    
    fallback = AsyncMock()
    
    router = JuryRoutingRouter(primary=primary, fallback=fallback, failure_threshold=2, recovery_seconds=60)
    req = JuryRoutingRequest(question_text="Q", expected_answer_points=[], student_answer="A", focus_type="TECHNICAL", strictness=1, interruption_level="MODERATE")
    
    res = await router.route(req)
    assert res.decision.action == JuryAction.NEXT_BANK
    primary.route.assert_called_once_with(req)
    fallback.route.assert_not_called()

@pytest.mark.asyncio
async def test_jury_router_fallback():
    primary = AsyncMock()
    primary.route.side_effect = JuryRoutingProviderError("Down", provider="groq")
    primary.name = "groq"
    
    fallback = AsyncMock()
    fallback.route.return_value = JuryRoutingDecision(action=JuryAction.FOLLOW_UP, follow_up_question="Q2")
    fallback.name = "gemini"
    fallback.model = "gemini"
    
    router = JuryRoutingRouter(primary=primary, fallback=fallback, failure_threshold=2, recovery_seconds=60)
    req = JuryRoutingRequest(question_text="Q", expected_answer_points=[], student_answer="A", focus_type="TECHNICAL", strictness=1, interruption_level="MODERATE")
    
    res = await router.route(req)
    assert res.decision.action == JuryAction.FOLLOW_UP
    assert res.fallback_used is True
    primary.route.assert_called_once_with(req)
    fallback.route.assert_called_once_with(req)
