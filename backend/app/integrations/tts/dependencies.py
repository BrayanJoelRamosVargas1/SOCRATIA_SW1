from functools import lru_cache

from app.core.config import get_settings
from app.integrations.tts.elevenlabs_tts import ElevenLabsTTSProvider
from app.integrations.tts.base import TTSProvider
from app.integrations.tts.local_tts import LocalTTSProvider


@lru_cache
def get_tts_provider() -> TTSProvider:
    settings = get_settings()
    if settings.voice_tts_enabled and settings.local_tts_enabled:
        return LocalTTSProvider(settings.local_tts_model_dir)
    return ElevenLabsTTSProvider(
        api_key=settings.elevenlabs_api_key.get_secret_value()
        if settings.voice_tts_enabled and settings.elevenlabs_api_key
        else None,
        default_voice_id=settings.elevenlabs_voice_id,
        timeout_seconds=30,
    )
