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

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class GroqQuestionGenerationProvider:
    name = "groq"

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        timeout_seconds: int,
        max_attempts: int,
        max_output_tokens: int,
        max_context_chars: int,
    ) -> None:
        self.api_key = api_key
        self._model = model
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.max_output_tokens = max_output_tokens
        self.max_context_chars = max_context_chars

    @property
    def model(self) -> str:
        return self._model

    def generate(self, request: QuestionGenerationRequest) -> GeneratedQuestionBank:
        if not self.api_key:
            raise QuestionGenerationProviderError(
                "Groq is not configured",
                provider=self.name,
                kind=LLMErrorKind.AUTH,
                detail="not_configured",
            )
        request = self._compact(request)
        last_error: QuestionGenerationProviderError | None = None
        for attempt in range(self.max_attempts):
            try:
                raw = self._request(request)
                bank = GeneratedQuestionBank.model_validate_json(raw)
                return validate_question_bank(bank, request)
            except (ValidationError, ValueError):
                last_error = QuestionGenerationProviderError(
                    "Groq returned an invalid question bank",
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
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_question_prompt(request)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "socratia_question_bank",
                    "strict": True,
                    "schema": QUESTION_BANK_JSON_SCHEMA,
                },
            },
            "temperature": 0.35,
            "max_completion_tokens": self.max_output_tokens,
        }
        try:
            response = httpx.post(
                GROQ_CHAT_COMPLETIONS_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise QuestionGenerationProviderError(
                "Groq could not be reached",
                provider=self.name,
                kind=LLMErrorKind.TRANSIENT,
                detail="network",
            ) from exc
        if response.status_code in {401, 403}:
            raise QuestionGenerationProviderError(
                "Groq authentication failed",
                provider=self.name,
                kind=LLMErrorKind.AUTH,
                detail=f"http_{response.status_code}",
            )
        if response.status_code in RETRYABLE_STATUS_CODES:
            raise QuestionGenerationProviderError(
                "Groq is temporarily unavailable",
                provider=self.name,
                kind=LLMErrorKind.TRANSIENT,
                detail=f"http_{response.status_code}",
            )
        if response.status_code == 400 and self._is_invalid_output_error(response):
            raise QuestionGenerationProviderError(
                "Groq returned an invalid structured response",
                provider=self.name,
                kind=LLMErrorKind.INVALID_OUTPUT,
                detail="json_validate_failed",
            )
        if response.is_error:
            raise QuestionGenerationProviderError(
                "Groq rejected the request",
                provider=self.name,
                kind=LLMErrorKind.PERMANENT,
                detail=f"http_{response.status_code}",
            )
        try:
            body = response.json()
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise QuestionGenerationProviderError(
                "Groq returned an invalid response",
                provider=self.name,
                kind=LLMErrorKind.INVALID_OUTPUT,
            ) from exc
        if not isinstance(text, str) or not text:
            raise QuestionGenerationProviderError(
                "Groq returned an empty response",
                provider=self.name,
                kind=LLMErrorKind.INVALID_OUTPUT,
            )
        return text

    def _compact(self, request: QuestionGenerationRequest) -> QuestionGenerationRequest:
        chunks = []
        used_chars = 0
        for chunk in request.chunks:
            remaining = self.max_context_chars - used_chars
            if remaining <= 0:
                break
            if len(chunk.text) <= remaining:
                chunks.append(chunk)
                used_chars += len(chunk.text)
            elif not chunks:
                chunks.append(
                    type(chunk)(id=chunk.id, text=chunk.text[:remaining], score=chunk.score)
                )
                used_chars += remaining
        return QuestionGenerationRequest(
            document_name=request.document_name,
            chunks=tuple(chunks),
        )

    @staticmethod
    def _is_invalid_output_error(response: httpx.Response) -> bool:
        try:
            body = response.json()
        except ValueError:
            return False
        error = body.get("error") if isinstance(body, dict) else None
        return isinstance(error, dict) and error.get("code") == "json_validate_failed"
