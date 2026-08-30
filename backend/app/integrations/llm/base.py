from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class QuestionCategory(StrEnum):
    CONCEPTUAL = "CONCEPTUAL"
    METHODOLOGICAL = "METHODOLOGICAL"
    TECHNICAL = "TECHNICAL"
    CRITICAL = "CRITICAL"


class QuestionDifficulty(StrEnum):
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class LLMErrorKind(StrEnum):
    AUTH = "auth"
    TRANSIENT = "transient"
    INVALID_OUTPUT = "invalid_output"
    PERMANENT = "permanent"
    CIRCUIT_OPEN = "circuit_open"


class QuestionGenerationProviderError(Exception):
    def __init__(
        self,
        message: str,
        *,
        provider: str,
        kind: LLMErrorKind,
        detail: str | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.kind = kind
        self.detail = detail

    @property
    def retryable(self) -> bool:
        return self.kind in {LLMErrorKind.TRANSIENT, LLMErrorKind.INVALID_OUTPUT}

    @property
    def telemetry_reason(self) -> str:
        suffix = f":{self.detail}" if self.detail else ""
        return f"{self.provider}:{self.kind.value}{suffix}"


class QuestionGenerationFailed(Exception):
    def __init__(
        self,
        *,
        primary_failure_reason: str,
        fallback_failure_reason: str,
        latency_ms: int,
    ) -> None:
        super().__init__("All question generation providers failed")
        self.primary_failure_reason = primary_failure_reason
        self.fallback_failure_reason = fallback_failure_reason
        self.latency_ms = latency_ms


@dataclass(frozen=True, slots=True)
class DocumentContextChunk:
    id: str
    text: str
    score: float


# Backwards-compatible public name retained for CU10.
QuestionContextChunk = DocumentContextChunk


@dataclass(frozen=True, slots=True)
class QuestionGenerationRequest:
    document_name: str
    chunks: tuple[DocumentContextChunk, ...]

    @property
    def allowed_chunk_ids(self) -> set[str]:
        return {chunk.id for chunk in self.chunks}


class GeneratedQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=12, max_length=1000)
    category: QuestionCategory
    difficulty: QuestionDifficulty
    source_chunk_ids: list[str] = Field(min_length=1, max_length=4)
    expected_answer_points: list[str] = Field(min_length=2, max_length=6)

    @field_validator("source_chunk_ids")
    @classmethod
    def source_ids_are_unique_and_non_empty(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned) or len(cleaned) != len(set(cleaned)):
            raise ValueError("source_chunk_ids must be unique and non-empty")
        return cleaned

    @field_validator("expected_answer_points")
    @classmethod
    def answer_points_are_useful(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(len(value) < 3 for value in cleaned):
            raise ValueError("expected_answer_points must contain useful text")
        return cleaned


class GeneratedQuestionBank(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[GeneratedQuestion] = Field(min_length=12, max_length=12)

    @model_validator(mode="after")
    def validate_distribution_and_uniqueness(self) -> "GeneratedQuestionBank":
        for category in QuestionCategory:
            count = sum(question.category == category for question in self.questions)
            if count != 3:
                raise ValueError(f"category {category.value} must contain exactly 3 questions")
        normalized = [question.question.casefold() for question in self.questions]
        if len(normalized) != len(set(normalized)):
            raise ValueError("questions must be unique")
        return self


@dataclass(frozen=True, slots=True)
class QuestionGenerationResult:
    bank: GeneratedQuestionBank
    provider: str
    model: str
    fallback_used: bool
    latency_ms: int
    primary_failure_reason: str | None


class QuestionGenerationProvider(Protocol):
    @property
    def name(self) -> str:
        """Return the provider name used in telemetry."""

    @property
    def model(self) -> str:
        """Return the provider model identifier."""

    def generate(self, request: QuestionGenerationRequest) -> GeneratedQuestionBank:
        """Generate and validate a structured question bank."""


def validate_question_bank(
    bank: GeneratedQuestionBank,
    request: QuestionGenerationRequest,
) -> GeneratedQuestionBank:
    allowed_ids = request.allowed_chunk_ids
    if not allowed_ids:
        raise ValueError("question generation context cannot be empty")
    for question in bank.questions:
        if not set(question.source_chunk_ids).issubset(allowed_ids):
            raise ValueError("question references chunks outside the supplied context")
    return bank


QUESTION_BANK_JSON_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": [category.value for category in QuestionCategory],
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": [difficulty.value for difficulty in QuestionDifficulty],
                    },
                    "source_chunk_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "expected_answer_points": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "question",
                    "category",
                    "difficulty",
                    "source_chunk_ids",
                    "expected_answer_points",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["questions"],
    "additionalProperties": False,
}
