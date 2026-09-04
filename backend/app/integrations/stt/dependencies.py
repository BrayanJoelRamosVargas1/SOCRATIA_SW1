from functools import lru_cache

from app.core.config import get_settings
from app.integrations.stt.gemini_stt import GeminiSTTProvider
from app.integrations.stt.groq_stt import GroqSTTProvider


class STTRouter:
    def __init__(self, primary: GroqSTTProvider, fallback: GeminiSTTProvider) -> None:
        self.primary = primary
        self.fallback = fallback

    async def transcribe(self, request) -> tuple[str, bool, int]:
        # return text, fallback_used, latency
        try:
            res = await self.primary.transcribe(request)
            return res.text, False, res.latency_ms
        except Exception:
            res = await self.fallback.transcribe(request)
            return res.text, True, res.latency_ms


@lru_cache
def get_stt_router() -> STTRouter:
    settings = get_settings()
    primary = GroqSTTProvider(
        api_key=settings.groq_api_key.get_secret_value() if settings.groq_api_key else None,
        model=settings.groq_stt_model,
        timeout_seconds=30,
        max_attempts=2,
    )
    fallback = GeminiSTTProvider(
        api_key=settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None,
        model="gemini-1.5-flash",  # Audio support model
        timeout_seconds=30,
        max_attempts=2,
    )
    return STTRouter(primary, fallback)
