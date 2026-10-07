import time

import httpx

from app.integrations.stt.base import STTProvider, STTProviderError, STTRequest, STTResult

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class GroqSTTProvider(STTProvider):
    name = "groq"

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

    async def transcribe(self, request: STTRequest) -> STTResult:
        if not self.api_key:
            raise STTProviderError("Groq STT is not configured", provider=self.name)

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
        # Determine extension based on mime_type (e.g., audio/webm -> .webm)
        extension = ".webm"
        if "ogg" in request.mime_type:
            extension = ".ogg"
        elif "wav" in request.mime_type:
            extension = ".wav"

        filename = f"audio{extension}"

        data = {
            "model": self.model,
            "response_format": "verbose_json",
            "timestamp_granularities[]": "segment",
            "language": "es",
        }
        if request.prompt:
            data["prompt"] = request.prompt

        files = {"file": (filename, request.audio_bytes, request.mime_type)}

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.post(
                    GROQ_STT_URL,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    data=data,
                    files=files,
                )
            except httpx.HTTPError as exc:
                raise STTProviderError(
                    "Groq could not be reached", provider=self.name, retryable=True
                ) from exc

        if response.status_code in {401, 403}:
            raise STTProviderError("Groq authentication failed", provider=self.name)
        if response.status_code in RETRYABLE_STATUS_CODES:
            raise STTProviderError(
                "Groq is temporarily unavailable", provider=self.name, retryable=True
            )
        if response.is_error:
            raise STTProviderError(
                f"Groq rejected the request: {response.status_code}", provider=self.name
            )

        try:
            body = response.json()
            text = body.get("text")
        except (ValueError, TypeError) as exc:
            raise STTProviderError("Groq returned an invalid response", provider=self.name) from exc

        if not isinstance(text, str):
            raise STTProviderError("Groq returned an empty response", provider=self.name)

        return text
