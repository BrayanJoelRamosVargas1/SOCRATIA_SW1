import time

import httpx
from pydantic import ValidationError

from app.integrations.llm.base import (
    QUESTION_BANK_JSON_SCHEMA,
    GeneratedQuestionBank,
    LLMErrorKind,
    QuestionGenerationProviderError,
    QuestionGenerationRequest,
    validate_question_bank,
)
from app.integrations.llm.prompt import SYSTEM_PROMPT, build_question_prompt

GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class GeminiQuestionGenerationProvider:
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

    def generate(self, request: QuestionGenerationRequest) -> GeneratedQuestionBank:
        if not self.api_key:
            raise QuestionGenerationProviderError(
                "Gemini is not configured",
                provider=self.name,
                kind=LLMErrorKind.AUTH,
                detail="not_configured",
            )
        last_error: QuestionGenerationProviderError | None = None
        for attempt in range(self.max_attempts):
            try:
                raw = self._request(request)
                bank = GeneratedQuestionBank.model_validate_json(raw)
                return validate_question_bank(bank, request)
            except (ValidationError, ValueError):
                last_error = QuestionGenerationProviderError(
                    "Gemini returned an invalid question bank",
                    provider=self.name,
                    kind=LLMErrorKind.INVALID_OUTPUT,
                )
            except QuestionGenerationProviderError as exc:
                last_error = exc
            if last_error is None or not last_error.retryable or attempt + 1 >= self.max_attempts:
                break
            time.sleep(2**attempt)
        assert last_error is not None
        raise last_error

    def _request(self, request: QuestionGenerationRequest) -> str:
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": build_question_prompt(request)}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": QUESTION_BANK_JSON_SCHEMA,
                "temperature": 0.35,
                "maxOutputTokens": self.max_output_tokens,
            },
        }
        try:
            response = httpx.post(
                f"{GEMINI_API_BASE_URL}/models/{self.model}:generateContent",
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key,
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise QuestionGenerationProviderError(
                "Gemini could not be reached",
                provider=self.name,
                kind=LLMErrorKind.TRANSIENT,
                detail="network",
            ) from exc
        if response.status_code in {401, 403}:
            raise QuestionGenerationProviderError(
                "Gemini authentication failed",
                provider=self.name,
                kind=LLMErrorKind.AUTH,
                detail=f"http_{response.status_code}",
            )
        if response.status_code in RETRYABLE_STATUS_CODES:
            raise QuestionGenerationProviderError(
                "Gemini is temporarily unavailable",
                provider=self.name,
                kind=LLMErrorKind.TRANSIENT,
                detail=f"http_{response.status_code}",
            )
        if response.is_error:
            raise QuestionGenerationProviderError(
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
            raise QuestionGenerationProviderError(
                "Gemini returned an invalid response",
                provider=self.name,
                kind=LLMErrorKind.INVALID_OUTPUT,
            ) from exc
        if not text:
            raise QuestionGenerationProviderError(
                "Gemini returned an empty response",
                provider=self.name,
                kind=LLMErrorKind.INVALID_OUTPUT,
            )
        return text
