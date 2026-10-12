import asyncio

import httpx
from pydantic import ValidationError

from app.integrations.llm.base import LLMErrorKind
from app.integrations.llm.jury_base import (
    JURY_ROUTING_JSON_SCHEMA,
    JuryRoutingDecision,
    JuryRoutingProvider,
    JuryRoutingProviderError,
    JuryRoutingRequest,
)
from app.integrations.llm.jury_prompt import SYSTEM_PROMPT, build_jury_prompt

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class GeminiJuryRoutingProvider(JuryRoutingProvider):
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        timeout_seconds: int,
        max_attempts: int,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> None:
        self.api_key = api_key
        self._model = model
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.temperature = temperature
        self.max_tokens = max_tokens

    @property
    def model(self) -> str:
        return self._model

    async def route(self, request: JuryRoutingRequest) -> JuryRoutingDecision:
        if not self.api_key:
            raise JuryRoutingProviderError(
                "Gemini is not configured",
                provider=self.name,
                kind=LLMErrorKind.AUTH,
                detail="not_configured",
            )
        last_error: JuryRoutingProviderError | None = None
        for attempt in range(self.max_attempts):
            try:
                raw = await self._request(request)
                return JuryRoutingDecision.model_validate_json(raw)
            except (ValidationError, ValueError):
                last_error = JuryRoutingProviderError(
                    "Gemini returned an invalid jury routing decision",
                    provider=self.name,
                    kind=LLMErrorKind.INVALID_OUTPUT,
                )
            except JuryRoutingProviderError as exc:
                last_error = exc
            if last_error is None or not last_error.retryable or attempt + 1 >= self.max_attempts:
                break
            await asyncio.sleep(2**attempt)
        assert last_error is not None
        raise last_error

    async def _request(self, request: JuryRoutingRequest) -> str:
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": build_jury_prompt(request)}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": JURY_ROUTING_JSON_SCHEMA,
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
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
                raise JuryRoutingProviderError(
                    "Gemini could not be reached",
                    provider=self.name,
                    kind=LLMErrorKind.TRANSIENT,
                    detail="network",
                ) from exc

        if response.status_code in {401, 403}:
            raise JuryRoutingProviderError(
                "Gemini authentication failed",
                provider=self.name,
                kind=LLMErrorKind.AUTH,
                detail=f"http_{response.status_code}",
            )
        if response.status_code in RETRYABLE_STATUS_CODES:
            raise JuryRoutingProviderError(
                "Gemini is temporarily unavailable",
                provider=self.name,
                kind=LLMErrorKind.TRANSIENT,
                detail=f"http_{response.status_code}",
            )
        if response.is_error:
            raise JuryRoutingProviderError(
                "Gemini rejected the request",
                provider=self.name,
                kind=LLMErrorKind.PERMANENT,
                detail=f"http_{response.status_code}",
            )
        try:
            body = response.json()
            parts = body["candidates"][0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise JuryRoutingProviderError(
                "Gemini returned an invalid response",
                provider=self.name,
                kind=LLMErrorKind.INVALID_OUTPUT,
            ) from exc
        if not text:
            raise JuryRoutingProviderError(
                "Gemini returned an empty response",
                provider=self.name,
                kind=LLMErrorKind.INVALID_OUTPUT,
            )
        return text
