"""Structured language-model contracts and resilient provider routing."""

from app.integrations.llm.base import (
    DocumentContextChunk,
    GeneratedQuestion,
    GeneratedQuestionBank,
    LLMErrorKind,
    QuestionCategory,
    QuestionContextChunk,
    QuestionDifficulty,
    QuestionGenerationFailed,
    QuestionGenerationProvider,
    QuestionGenerationProviderError,
    QuestionGenerationRequest,
    QuestionGenerationResult,
)
from app.integrations.llm.presentation import (
    GeneratedPresentation,
    GeneratedSlide,
    PresentationGenerationFailed,
    PresentationGenerationProviderError,
    PresentationGenerationRequest,
    PresentationGenerationResult,
)
from app.integrations.llm.presentation_router import PresentationGenerationRouter
from app.integrations.llm.router import QuestionGenerationRouter

__all__ = [
    "DocumentContextChunk",
    "GeneratedPresentation",
    "GeneratedQuestion",
    "GeneratedQuestionBank",
    "GeneratedSlide",
    "LLMErrorKind",
    "PresentationGenerationFailed",
    "PresentationGenerationProviderError",
    "PresentationGenerationRequest",
    "PresentationGenerationResult",
    "PresentationGenerationRouter",
    "QuestionCategory",
    "QuestionContextChunk",
    "QuestionDifficulty",
    "QuestionGenerationFailed",
    "QuestionGenerationProvider",
    "QuestionGenerationProviderError",
    "QuestionGenerationRequest",
    "QuestionGenerationResult",
    "QuestionGenerationRouter",
]
