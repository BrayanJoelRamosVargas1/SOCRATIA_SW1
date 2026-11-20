from copy import deepcopy
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.integrations.llm.base import (
    DocumentContextChunk,
    LLMErrorKind,
    QuestionGenerationProviderError,
)

WORDS_PER_MINUTE = 130


class PresentationGenerationProviderError(QuestionGenerationProviderError):
    """Provider error for CU11; shares CU10 retry semantics."""


class PresentationGenerationFailed(Exception):
    def __init__(
        self,
        *,
        primary_failure_reason: str,
        fallback_failure_reason: str,
        latency_ms: int,
    ) -> None:
        super().__init__("All presentation generation providers failed")
        self.primary_failure_reason = primary_failure_reason
        self.fallback_failure_reason = fallback_failure_reason
        self.latency_ms = latency_ms


@dataclass(frozen=True, slots=True)
class PresentationGenerationRequest:
    document_name: str
    duration_minutes: int
    chunks: tuple[DocumentContextChunk, ...]

    @property
    def target_word_count(self) -> int:
        return self.duration_minutes * WORDS_PER_MINUTE

    @property
    def allowed_chunk_ids(self) -> set[str]:
        return {chunk.id for chunk in self.chunks}


class GeneratedSlide(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    position: int = Field(ge=1, le=18)
    title: str = Field(min_length=3, max_length=160)
    objective: str = Field(min_length=8, max_length=500)
    bullet_points: list[str] = Field(min_length=2, max_length=5)
    speaker_notes: str = Field(min_length=30, max_length=5000)
    estimated_seconds: int = Field(ge=20, le=600)
    source_chunk_ids: list[str] = Field(min_length=1, max_length=4)

    @field_validator("bullet_points")
    @classmethod
    def bullets_are_useful(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(len(value) < 3 for value in cleaned):
            raise ValueError("bullet_points must contain useful text")
        return cleaned

    @field_validator("source_chunk_ids")
    @classmethod
    def source_ids_are_unique(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned) or len(cleaned) != len(set(cleaned)):
            raise ValueError("source_chunk_ids must be unique and non-empty")
        return cleaned


class GeneratedPresentation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=200)
    total_duration_minutes: int = Field(ge=5, le=30)
    target_word_count: int = Field(ge=650, le=3900)
    slides: list[GeneratedSlide] = Field(min_length=4, max_length=18)

    @model_validator(mode="after")
    def positions_and_titles_are_unique(self) -> "GeneratedPresentation":
        positions = [slide.position for slide in self.slides]
        if positions != list(range(1, len(self.slides) + 1)):
            raise ValueError("slide positions must be consecutive and start at 1")
        titles = [slide.title.casefold() for slide in self.slides]
        if len(titles) != len(set(titles)):
            raise ValueError("slide titles must be unique")
        return self


@dataclass(frozen=True, slots=True)
class PresentationGenerationResult:
    presentation: GeneratedPresentation
    provider: str
    model: str
    fallback_used: bool
    latency_ms: int
    primary_failure_reason: str | None


class PresentationGenerationProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def model(self) -> str: ...

    def generate(self, request: PresentationGenerationRequest) -> GeneratedPresentation: ...


def slide_count_range(duration_minutes: int) -> tuple[int, int]:
    if duration_minutes <= 7:
        return 4, 6
    if duration_minutes <= 12:
        return 6, 9
    if duration_minutes <= 17:
        return 8, 12
    if duration_minutes <= 24:
        return 10, 14
    return 14, 18


def validate_presentation(
    presentation: GeneratedPresentation,
    request: PresentationGenerationRequest,
) -> GeneratedPresentation:
    from app.core.spanish import require_spanish
    require_spanish(presentation.title)
    if not request.allowed_chunk_ids:
        raise ValueError("presentation context cannot be empty")
    if presentation.total_duration_minutes != request.duration_minutes:
        raise ValueError("presentation duration does not match the request")
    if presentation.target_word_count != request.target_word_count:
        raise ValueError("presentation word budget does not match the request")
    minimum_slides, maximum_slides = slide_count_range(request.duration_minutes)
    if not minimum_slides <= len(presentation.slides) <= maximum_slides:
        raise ValueError("slide count is outside the duration heuristic")
    total_seconds = sum(slide.estimated_seconds for slide in presentation.slides)
    requested_seconds = request.duration_minutes * 60
    if not requested_seconds * 0.9 <= total_seconds <= requested_seconds * 1.1:
        raise ValueError("estimated presentation duration is outside the 10 percent tolerance")
    for slide in presentation.slides:
        require_spanish(slide.title, slide.objective, slide.speaker_notes, " ".join(slide.bullet_points))
        if not set(slide.source_chunk_ids).issubset(request.allowed_chunk_ids):
            raise ValueError("slide references chunks outside the supplied context")
    return presentation


PRESENTATION_JSON_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "total_duration_minutes": {"type": "integer"},
        "target_word_count": {"type": "integer"},
        "slides": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "position": {"type": "integer"},
                    "title": {"type": "string"},
                    "objective": {"type": "string"},
                    "bullet_points": {"type": "array", "items": {"type": "string"}},
                    "speaker_notes": {"type": "string"},
                    "estimated_seconds": {"type": "integer"},
                    "source_chunk_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "position",
                    "title",
                    "objective",
                    "bullet_points",
                    "speaker_notes",
                    "estimated_seconds",
                    "source_chunk_ids",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "total_duration_minutes", "target_word_count", "slides"],
    "additionalProperties": False,
}


def presentation_json_schema(request: PresentationGenerationRequest) -> dict:
    """Constrain generation with the same bounds enforced after the response.

    Previously the API schema permitted six bullets although our validator
    rejected them, causing complete regenerations of otherwise useful slides.
    """
    schema = deepcopy(PRESENTATION_JSON_SCHEMA)
    properties = schema["properties"]
    properties["title"].update(minLength=3, maxLength=200)
    properties["total_duration_minutes"]["enum"] = [request.duration_minutes]
    properties["target_word_count"]["enum"] = [request.target_word_count]
    minimum, maximum = slide_count_range(request.duration_minutes)
    properties["slides"].update(minItems=minimum, maxItems=maximum)
    slide = properties["slides"]["items"]["properties"]
    slide["position"].update(minimum=1, maximum=18)
    slide["title"].update(minLength=3, maxLength=160)
    slide["objective"].update(minLength=8, maxLength=500)
    slide["speaker_notes"].update(minLength=30, maxLength=5000)
    slide["estimated_seconds"].update(minimum=20, maximum=600)
    slide["bullet_points"].update(minItems=2, maxItems=5)
    slide["bullet_points"]["items"]["minLength"] = 3
    slide["source_chunk_ids"].update(minItems=1, maxItems=4)
    slide["source_chunk_ids"]["items"]["enum"] = sorted(request.allowed_chunk_ids)
    return schema


def parse_generated_presentation(raw: str, request: PresentationGenerationRequest) -> GeneratedPresentation:
    presentation = GeneratedPresentation.model_validate_json(raw)
    total = sum(slide.estimated_seconds for slide in presentation.slides)
    target = request.duration_minutes * 60
    if not target * 0.9 <= total <= target * 1.1:
        # These are rehearsal time allocations, not claims from the source.
        # Fit the requested schedule without regenerating or changing any prose.
        weights = [slide.estimated_seconds for slide in presentation.slides]
        if len(weights) * 20 <= target <= len(weights) * 600:
            pending = set(range(len(weights)))
            seconds = [0] * len(weights)
            remaining = target
            while pending:
                denominator = sum(weights[i] for i in pending)
                proposed = {i: remaining * weights[i] / denominator for i in pending}
                bounded = {i: 20 if value < 20 else 600 for i, value in proposed.items()
                           if value < 20 or value > 600}
                if bounded:
                    for i, value in bounded.items():
                        seconds[i] = value
                        remaining -= value
                        pending.remove(i)
                    continue
                for i, value in proposed.items():
                    seconds[i] = int(value)
                remainder = remaining - sum(seconds[i] for i in pending)
                for i in sorted(pending, key=lambda i: (-(proposed[i] - seconds[i]), i))[:remainder]:
                    seconds[i] += 1
                break
            presentation = presentation.model_copy(update={"slides": [
                slide.model_copy(update={"estimated_seconds": seconds[i]})
                for i, slide in enumerate(presentation.slides)
            ]})
    return validate_presentation(presentation, request)


__all__ = [
    "GeneratedPresentation",
    "GeneratedSlide",
    "LLMErrorKind",
    "PRESENTATION_JSON_SCHEMA",
    "PresentationGenerationFailed",
    "PresentationGenerationProvider",
    "PresentationGenerationProviderError",
    "PresentationGenerationRequest",
    "PresentationGenerationResult",
    "WORDS_PER_MINUTE",
    "slide_count_range",
    "validate_presentation",
]
