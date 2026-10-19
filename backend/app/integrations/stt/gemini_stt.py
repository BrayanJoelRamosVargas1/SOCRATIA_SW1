import asyncio
import base64
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
            interaction = await asyncio.wait_for(self.client.aio.interactions.create(
                model=self.model,
                input=[
                    {
                        "type": "audio",
                        "mime_type": request.mime_type.split(';', 1)[0].strip().lower(),
                        "data": base64.b64encode(request.audio_bytes).decode('ascii'),
                    }
                ],
                generation_config={"transcription_config": {"language_codes": ["es-419"], "mode": {"type":"verbatim"}}},
                store=False,
                timeout=self.timeout_seconds,
            ), timeout=self.timeout_seconds)
        except TimeoutError as exc:
            raise STTProviderError("Gemini transcription timed out", provider=self.name, retryable=True) from exc
        except APIError as exc:
            retryable = exc.code in {408, 429, 500, 502, 503, 504}
            raise STTProviderError(
                f"Gemini API error: {exc.code}", provider=self.name, retryable=retryable
            ) from exc
        except Exception as exc:
            # Interactions uses a separate status-code exception hierarchy in
            # SDK 2.x. Do not expose its request/body details in user errors.
            status = getattr(exc, 'status_code', None)
            raise STTProviderError(
                "Gemini transcription request failed", provider=self.name,
                retryable=status in {408, 429, 500, 502, 503, 504}
            ) from exc

        text = getattr(interaction, 'output_text', None)
        # The installed SDK exposes typed text outputs, while newer releases
        # also provide the documented output_text convenience property.
        if not isinstance(text, str):
            text = ''.join(output.text for output in (getattr(interaction, 'outputs', None) or [])
                if getattr(output, 'type', None) == 'text' and isinstance(getattr(output, 'text', None), str))
        if not text.strip():
            raise STTProviderError("Gemini returned an empty response", provider=self.name)

        return text.strip()
