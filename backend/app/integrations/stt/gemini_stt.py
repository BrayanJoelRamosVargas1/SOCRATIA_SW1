import time

from google import genai
from google.genai.errors import APIError

from app.integrations.stt.base import STTProvider, STTProviderError, STTRequest, STTResult


class GeminiSTTProvider(STTProvider):
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        timeout_seconds: int,
        max_attempts: int,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.client = genai.Client(api_key=api_key) if api_key else None

    async def transcribe(self, request: STTRequest) -> STTResult:
        if not self.client:
            raise STTProviderError("Gemini STT is not configured", provider=self.name)

        start_time = time.monotonic()
        last_error: STTProviderError | None = None

        for attempt in range(self.max_attempts):
            try:
                text = await self._request(request)
                latency_ms = int((time.monotonic() - start_time) * 1000)
                return STTResult(
                    text=text,
                    latency_ms=latency_ms,
                    provider=self.name,
                    model=self.model,
                )
            except STTProviderError as exc:
                last_error = exc
            if not last_error.retryable or attempt + 1 >= self.max_attempts:
                break
        assert last_error is not None
        raise last_error

    async def _request(self, request: STTRequest) -> str:
        try:
            # We use a config dict natively to avoid import issues or exact type names
            # since google-genai accepts dictionaries for config objects
            interaction = await self.client.aio.interactions.create(
                model=self.model,
                input=[
                    {
                        "type": "audio",
                        "mime_type": request.mime_type,
                        "data": request.audio_bytes,
                    }
                ],
                config={
                    "transcription_config": {
                        "language_codes": ["es-419"],
                        "mode": "VERBATIM"
                    }
                }
            )
        except APIError as exc:
            retryable = exc.code in {408, 429, 500, 502, 503, 504}
            raise STTProviderError(f"Gemini API error: {str(exc)}", provider=self.name, retryable=retryable) from exc
        except Exception as exc:
            raise STTProviderError(f"Gemini request failed: {str(exc)}", provider=self.name, retryable=False) from exc
        
        text = interaction.text
        if not text:
            raise STTProviderError("Gemini returned an empty response", provider=self.name)

        return text.strip()
