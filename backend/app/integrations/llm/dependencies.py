from functools import lru_cache

from app.core.config import get_settings
from app.integrations.llm.gemini import GeminiQuestionGenerationProvider
from app.integrations.llm.groq import GroqQuestionGenerationProvider
from app.integrations.llm.presentation_gemini import GeminiPresentationGenerationProvider
from app.integrations.llm.presentation_groq import GroqPresentationGenerationProvider
from app.integrations.llm.presentation_router import PresentationGenerationRouter
from app.integrations.llm.router import QuestionGenerationRouter


@lru_cache
def get_question_generation_router() -> QuestionGenerationRouter:
    settings = get_settings()
    primary = GeminiQuestionGenerationProvider(
        api_key=(settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None),
        model=settings.gemini_question_model,
        timeout_seconds=settings.question_generation_timeout_seconds,
        max_attempts=settings.question_generation_max_attempts,
        max_output_tokens=settings.gemini_question_max_output_tokens,
    )
    fallback = GroqQuestionGenerationProvider(
        api_key=settings.groq_api_key.get_secret_value() if settings.groq_api_key else None,
        model=settings.groq_question_model,
        timeout_seconds=settings.question_generation_timeout_seconds,
        max_attempts=settings.question_generation_max_attempts,
        max_output_tokens=settings.groq_question_max_output_tokens,
        max_context_chars=settings.groq_question_max_context_chars,
    )
    return QuestionGenerationRouter(
        primary=primary,
        fallback=fallback,
        failure_threshold=settings.question_circuit_breaker_threshold,
        recovery_seconds=settings.question_circuit_breaker_recovery_seconds,
    )


@lru_cache
def get_presentation_generation_router() -> PresentationGenerationRouter:
    settings = get_settings()
    primary = GeminiPresentationGenerationProvider(
        api_key=(settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None),
        model=settings.gemini_question_model,
        timeout_seconds=settings.question_generation_timeout_seconds,
        max_attempts=settings.question_generation_max_attempts,
        max_output_tokens=settings.gemini_question_max_output_tokens,
    )
    fallback = GroqPresentationGenerationProvider(
        api_key=settings.groq_api_key.get_secret_value() if settings.groq_api_key else None,
        model=settings.groq_question_model,
        timeout_seconds=settings.question_generation_timeout_seconds,
        max_attempts=settings.question_generation_max_attempts,
        max_output_tokens=settings.groq_question_max_output_tokens,
        max_context_chars=settings.groq_question_max_context_chars,
    )
    return PresentationGenerationRouter(
        primary=primary,
        fallback=fallback,
        failure_threshold=settings.question_circuit_breaker_threshold,
        recovery_seconds=settings.question_circuit_breaker_recovery_seconds,
    )
