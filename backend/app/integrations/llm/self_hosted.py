"""Authenticated OpenAI-compatible inference on an operator-managed GPU.

No model downloads or local inference in the API process. The endpoint is trusted
operator configuration, never user input. Redirects are deliberately disabled.
"""

from pathlib import Path

import httpx

from app.core.config import get_settings
from app.integrations.llm.base import (
    GeneratedQuestionBank,
    LLMErrorKind,
    QuestionGenerationProviderError,
    validate_question_bank,
)
from app.integrations.llm.presentation import (
    GeneratedPresentation,
    PresentationGenerationProviderError,
    validate_presentation,
)
from app.integrations.llm.presentation_prompt import (
    PRESENTATION_SYSTEM_PROMPT,
    build_presentation_prompt,
)
from app.integrations.llm.prompt import SYSTEM_PROMPT, build_question_prompt


def is_configured(settings=None):
    settings = settings or get_settings()
    return bool(
        settings.self_hosted_llm_url
        and (settings.self_hosted_llm_key or settings.self_hosted_llm_key_file)
    )


def _private_key(settings):
    if settings.self_hosted_llm_key:
        return settings.self_hosted_llm_key.get_secret_value()
    # This is operator configuration, never a path accepted from a chat request.
    key = Path(settings.self_hosted_llm_key_file).read_text().strip()
    if not key or len(key) > 256 or any(char.isspace() for char in key):
        raise ValueError("invalid_private_model_key")
    return key


def completion(system, prompt, schema=None, max_tokens=4096, *, timeout_seconds=None):
    s = get_settings()
    if not is_configured(s):
        raise RuntimeError("self_hosted_not_configured")
    payload = {
        "model": s.self_hosted_llm_model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if schema is not None:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "socratia", "strict": True, "schema": schema},
        }
    with httpx.Client(
        timeout=httpx.Timeout(
            timeout_seconds
            if timeout_seconds is not None
            else s.question_generation_timeout_seconds,
            connect=5,
        ),
        follow_redirects=False,
    ) as client:
        r = client.post(
            s.self_hosted_llm_url.rstrip("/") + "/chat/completions",
            headers={"Authorization": "Bearer " + _private_key(s)},
            json=payload,
        )
        r.raise_for_status()
        if len(r.content) > 200000:
            raise ValueError("response_too_large")
        choice = r.json()["choices"][0]
        if choice.get("finish_reason") != "stop":
            raise ValueError("incomplete_response")
        content = choice["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty_response")
        return content


class SelfHostedQuestions:
    name = "self_hosted"

    @property
    def model(self):
        return get_settings().self_hosted_llm_model

    def generate(self, request):
        try:
            raw = completion(
                SYSTEM_PROMPT,
                build_question_prompt(request),
                GeneratedQuestionBank.model_json_schema(),
            )
            return validate_question_bank(GeneratedQuestionBank.model_validate_json(raw), request)
        except Exception:
            raise QuestionGenerationProviderError(
                "Modelo propio no disponible",
                provider=self.name,
                kind=LLMErrorKind.TRANSIENT,
                detail="inference_failed",
            ) from None


class SelfHostedPresentation:
    name = "self_hosted"

    @property
    def model(self):
        return get_settings().self_hosted_llm_model

    def generate(self, request):
        try:
            raw = completion(
                PRESENTATION_SYSTEM_PROMPT,
                build_presentation_prompt(request),
                GeneratedPresentation.model_json_schema(),
            )
            return validate_presentation(GeneratedPresentation.model_validate_json(raw), request)
        except Exception:
            raise PresentationGenerationProviderError(
                "Modelo propio no disponible",
                provider=self.name,
                kind=LLMErrorKind.TRANSIENT,
                detail="inference_failed",
            ) from None
