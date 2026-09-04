import asyncio
import time

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

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class GroqJuryRoutingProvider(JuryRoutingProvider):
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
        self._model = model
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts

    @property
    def model(self) -> str:
        return self._model

    async def route(self, request: JuryRoutingRequest) -> JuryRoutingDecision:
        if not self.api_key:
            raise JuryRoutingProviderError(
                "Groq is not configured",
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
                    "Groq returned an invalid jury routing decision",
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
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_jury_prompt(request)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "jury_routing_decision",
                    "strict": True,
                    "schema": JURY_ROUTING_JSON_SCHEMA,
                },
            },
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.post(
                    GROQ_CHAT_COMPLETIONS_URL,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            except httpx.HTTPError as exc:
                raise JuryRoutingProviderError(
                    "Groq could not be reached",
                    provider=self.name,
                    kind=LLMErrorKind.TRANSIENT,
                    detail="network",
                ) from exc

        if response.status_code in {401, 403}:
            raise JuryRoutingProviderError(
                "Groq authentication failed",
                provider=self.name,
                kind=LLMErrorKind.AUTH,
                detail=f"http_{response.status_code}",
            )
        if response.status_code in RETRYABLE_STATUS_CODES:
            raise JuryRoutingProviderError(
                "Groq is temporarily unavailable",
                provider=self.name,
                kind=LLMErrorKind.TRANSIENT,
                detail=f"http_{response.status_code}",
            )
        if response.status_code == 400 and self._is_invalid_output_error(response):
            raise JuryRoutingProviderError(
                "Groq returned an invalid structured response",
                provider=self.name,
                kind=LLMErrorKind.INVALID_OUTPUT,
                detail="json_validate_failed",
            )
        if response.is_error:
            raise JuryRoutingProviderError(
                "Groq rejected the request",
                provider=self.name,
                kind=LLMErrorKind.PERMANENT,
                detail=f"http_{response.status_code}",
            )
        try:
            body = response.json()
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise JuryRoutingProviderError(
                "Groq returned an invalid response",
                provider=self.name,
                kind=LLMErrorKind.INVALID_OUTPUT,
            ) from exc
        if not isinstance(text, str) or not text:
            raise JuryRoutingProviderError(
                "Groq returned an empty response",
                provider=self.name,
                kind=LLMErrorKind.INVALID_OUTPUT,
            )
        return text

    @staticmethod
    def _is_invalid_output_error(response: httpx.Response) -> bool:
        try:
            body = response.json()
        except ValueError:
            return False
        error = body.get("error") if isinstance(body, dict) else None
        return isinstance(error, dict) and error.get("code") == "json_validate_failed"
