import base64
import time

import httpx

from app.integrations.stt.base import STTProvider, STTProviderError, STTRequest, STTResult

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


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

    async def transcribe(self, request: STTRequest) -> STTResult:
        if not self.api_key:
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
        prompt_text = (
            "Please provide a verbatim transcription of this audio, with no additional commentary."
        )
        if request.prompt:
            prompt_text += f"\nContext/Prompt: {request.prompt}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt_text},
                        {
                            "inlineData": {
                                "mimeType": request.mime_type,
                                "data": base64.b64encode(request.audio_bytes).decode("ascii"),
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.post(
                    f"{GEMINI_API_BASE_URL}/models/{self.model}:generateContent",
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": self.api_key,
                    },
                    json=payload,
                )
            except httpx.HTTPError as exc:
                raise STTProviderError(
                    "Gemini could not be reached", provider=self.name, retryable=True
                ) from exc

        if response.status_code in {401, 403}:
            raise STTProviderError("Gemini authentication failed", provider=self.name)
        if response.status_code in RETRYABLE_STATUS_CODES:
            raise STTProviderError(
                "Gemini is temporarily unavailable", provider=self.name, retryable=True
            )
        if response.is_error:
            raise STTProviderError(
                f"Gemini rejected the request: {response.status_code}", provider=self.name
            )

        try:
            body = response.json()
            parts = body["candidates"][0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise STTProviderError(
                "Gemini returned an invalid response", provider=self.name
            ) from exc

        if not text:
            raise STTProviderError("Gemini returned an empty response", provider=self.name)

        return text.strip()
