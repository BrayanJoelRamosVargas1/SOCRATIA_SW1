import time

import httpx
from pydantic import ValidationError

from app.integrations.llm.base import LLMErrorKind
from app.integrations.llm.gemini import GEMINI_API_BASE_URL, RETRYABLE_STATUS_CODES
from app.integrations.llm.presentation import (
    PRESENTATION_JSON_SCHEMA,
    GeneratedPresentation,
    PresentationGenerationProviderError,
    PresentationGenerationRequest,
    validate_presentation,
)
from app.integrations.llm.presentation_prompt import (
    PRESENTATION_SYSTEM_PROMPT,
    build_presentation_prompt,
)


class GeminiPresentationGenerationProvider:
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        timeout_seconds: int,
        max_attempts: int,
        max_output_tokens: int,
    ) -> None:
        self.api_key = api_key
        self._model = model
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.max_output_tokens = max_output_tokens

    @property
    def model(self) -> str:
        return self._model

    def generate(self, request: PresentationGenerationRequest) -> GeneratedPresentation:
        if not self.api_key:
            raise PresentationGenerationProviderError(
                "Gemini is not configured",
                provider=self.name,
                kind=LLMErrorKind.AUTH,
                detail="not_configured",
            )
        last_error: PresentationGenerationProviderError | None = None
        for attempt in range(self.max_attempts):
            try:
                result = GeneratedPresentation.model_validate_json(self._request(request))
                return validate_presentation(result, request)
            except (ValidationError, ValueError):
                last_error = PresentationGenerationProviderError(
                    "Gemini returned invalid presentation material",
                    provider=self.name,
                    kind=LLMErrorKind.INVALID_OUTPUT,
                )
            except PresentationGenerationProviderError as exc:
                last_error = exc
            if not last_error.retryable or attempt + 1 >= self.max_attempts:
                break
            time.sleep(2**attempt)
        assert last_error is not None
        raise last_error

    def _request(self, request: PresentationGenerationRequest) -> str:
        payload = {
            "systemInstruction": {"parts": [{"text": PRESENTATION_SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": build_presentation_prompt(request)}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": PRESENTATION_JSON_SCHEMA,
                "temperature": 0.3,
                "maxOutputTokens": self.max_output_tokens,
            },
        }
        try:
            response = httpx.post(
                f"{GEMINI_API_BASE_URL}/models/{self.model}:generateContent",
                headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
                json=payload,
                timeout=self.timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise PresentationGenerationProviderError(
                "Gemini could not be reached",
                provider=self.name,
                kind=LLMErrorKind.TRANSIENT,
                detail="network",
            ) from exc
        if response.status_code in {401, 403}:
            raise PresentationGenerationProviderError(
                "Gemini authentication failed",
                provider=self.name,
                kind=LLMErrorKind.AUTH,
                detail=f"http_{response.status_code}",
            )
        if response.status_code in RETRYABLE_STATUS_CODES:
            raise PresentationGenerationProviderError(
                "Gemini is temporarily unavailable",
                provider=self.name,
                kind=LLMErrorKind.TRANSIENT,
                detail=f"http_{response.status_code}",
            )
        if response.is_error:
            raise PresentationGenerationProviderError(
                "Gemini rejected the request",
                provider=self.name,
                kind=LLMErrorKind.PERMANENT,
                detail=f"http_{response.status_code}",
            )
        try:
            parts = response.json()["candidates"][0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise PresentationGenerationProviderError(
                "Gemini returned an invalid response",
                provider=self.name,
                kind=LLMErrorKind.INVALID_OUTPUT,
            ) from exc
        if not text:
            raise PresentationGenerationProviderError(
                "Gemini returned an empty response",
                provider=self.name,
                kind=LLMErrorKind.INVALID_OUTPUT,
            )
        return text
