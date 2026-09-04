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
from app.integrations.llm.jury_base import (
    JuryAction,
    JuryRoutingDecision,
    JuryRoutingFailed,
    JuryRoutingProvider,
    JuryRoutingProviderError,
    JuryRoutingRequest,
    JuryRoutingResult,
)
from app.integrations.llm.presentation import (
    GeneratedPresentation,
    GeneratedSlide,
    PresentationGenerationFailed,
    PresentationGenerationProviderError,
    PresentationGenerationResult,
)
from app.integrations.llm.presentation_router import PresentationGenerationRouter
from app.integrations.llm.router import QuestionGenerationRouter
from app.integrations.llm.jury_router import JuryRoutingRouter

__all__ = [
    "DocumentContextChunk",
    "GeneratedPresentation",
    "GeneratedQuestion",
    "GeneratedQuestionBank",
    "GeneratedSlide",
    "JuryAction",
    "JuryRoutingDecision",
    "JuryRoutingFailed",
    "JuryRoutingProvider",
    "JuryRoutingProviderError",
    "JuryRoutingRequest",
    "JuryRoutingResult",
    "JuryRoutingRouter",
    "LLMErrorKind",
    "PresentationGenerationFailed",
    "PresentationGenerationProviderError",
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
