from functools import lru_cache

from app.core.config import get_settings
from app.integrations.tts.elevenlabs_tts import ElevenLabsTTSProvider


@lru_cache
def get_tts_provider() -> ElevenLabsTTSProvider:
    settings = get_settings()
    return ElevenLabsTTSProvider(
        api_key=settings.elevenlabs_api_key.get_secret_value() if settings.elevenlabs_api_key else None,
        default_voice_id=settings.elevenlabs_voice_id,
        timeout_seconds=30,
    )
