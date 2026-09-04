import json
from typing import AsyncIterator

import httpx

from app.integrations.tts.base import TTSProvider, TTSProviderError, TTSRequest

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"


class ElevenLabsTTSProvider(TTSProvider):
    name = "elevenlabs"

    def __init__(
        self,
        *,
        api_key: str | None,
        default_voice_id: str | None,
        timeout_seconds: int,
    ) -> None:
        self.api_key = api_key
        self.default_voice_id = default_voice_id
        self.timeout_seconds = timeout_seconds

    async def synthesize(self, request: TTSRequest) -> AsyncIterator[bytes]:
        if not self.api_key:
            raise TTSProviderError("ElevenLabs TTS is not configured", provider=self.name)
            
        voice_id = request.voice_id or self.default_voice_id
        if not voice_id:
            raise TTSProviderError("ElevenLabs voice ID is not configured", provider=self.name)

        url = ELEVENLABS_TTS_URL.format(voice_id=voice_id)
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key,
        }
        
        payload = {
            "text": request.text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            }
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code in {401, 403}:
                        raise TTSProviderError("ElevenLabs authentication failed", provider=self.name)
                    if response.status_code == 429:
                        raise TTSProviderError("ElevenLabs rate limit exceeded", provider=self.name, retryable=True)
                    if response.is_error:
                        try:
                            # Attempt to read error detail if small enough
                            await response.aread()
                            detail = response.json()
                        except (ValueError, httpx.StreamError):
                            detail = response.text
                        raise TTSProviderError(f"ElevenLabs rejected the request: {response.status_code} {detail}", provider=self.name)

                    async for chunk in response.aiter_bytes():
                        if chunk:
                            yield chunk
                            
            except httpx.HTTPError as exc:
                raise TTSProviderError(
                    "ElevenLabs could not be reached", provider=self.name, retryable=True
                ) from exc
