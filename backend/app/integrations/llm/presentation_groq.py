import time

import httpx
from pydantic import ValidationError

from app.integrations.llm.base import DocumentContextChunk, LLMErrorKind
from app.integrations.llm.groq import GROQ_CHAT_COMPLETIONS_URL, RETRYABLE_STATUS_CODES
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


class GroqPresentationGenerationProvider:
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

    def generate(self, request: PresentationGenerationRequest) -> GeneratedPresentation:
        if not self.api_key:
            raise PresentationGenerationProviderError(
                "Groq is not configured",
                provider=self.name,
                kind=LLMErrorKind.AUTH,
                detail="not_configured",
            )
        request = self._compact(request)
        last_error: PresentationGenerationProviderError | None = None
        for attempt in range(self.max_attempts):
            try:
                result = GeneratedPresentation.model_validate_json(self._request(request))
                return validate_presentation(result, request)
            except (ValidationError, ValueError):
                last_error = PresentationGenerationProviderError(
                    "Groq returned invalid presentation material",
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
            "model": self.model,
            "messages": [
                {"role": "system", "content": PRESENTATION_SYSTEM_PROMPT},
                {"role": "user", "content": build_presentation_prompt(request)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "socratia_presentation_material",
                    "strict": True,
                    "schema": PRESENTATION_JSON_SCHEMA,
                },
            },
            "temperature": 0.3,
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
            raise PresentationGenerationProviderError(
                "Groq could not be reached",
                provider=self.name,
                kind=LLMErrorKind.TRANSIENT,
                detail="network",
            ) from exc
        if response.status_code in {401, 403}:
            kind = LLMErrorKind.AUTH
        elif response.status_code in RETRYABLE_STATUS_CODES:
            kind = LLMErrorKind.TRANSIENT
        elif response.status_code == 400 and self._is_invalid_output_error(response):
            kind = LLMErrorKind.INVALID_OUTPUT
        elif response.is_error:
            kind = LLMErrorKind.PERMANENT
        else:
            kind = None
        if kind is not None:
            raise PresentationGenerationProviderError(
                "Groq presentation request failed",
                provider=self.name,
                kind=kind,
                detail=f"http_{response.status_code}",
            )
        try:
            text = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise PresentationGenerationProviderError(
                "Groq returned an invalid response",
                provider=self.name,
                kind=LLMErrorKind.INVALID_OUTPUT,
            ) from exc
        if not isinstance(text, str) or not text:
            raise PresentationGenerationProviderError(
                "Groq returned an empty response",
                provider=self.name,
                kind=LLMErrorKind.INVALID_OUTPUT,
            )
        return text

    def _compact(self, request: PresentationGenerationRequest) -> PresentationGenerationRequest:
        chunks: list[DocumentContextChunk] = []
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
                    DocumentContextChunk(
                        id=chunk.id,
                        text=chunk.text[:remaining],
                        score=chunk.score,
                    )
                )
        return PresentationGenerationRequest(
            document_name=request.document_name,
            duration_minutes=request.duration_minutes,
            chunks=tuple(chunks),
        )

    @staticmethod
    def _is_invalid_output_error(response: httpx.Response) -> bool:
        try:
            error = response.json().get("error")
        except (AttributeError, ValueError):
            return False
        return isinstance(error, dict) and error.get("code") == "json_validate_failed"
