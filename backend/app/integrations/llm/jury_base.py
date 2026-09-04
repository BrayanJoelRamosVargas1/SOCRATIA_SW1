from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.integrations.llm.base import LLMErrorKind


class JuryAction(StrEnum):
    NEXT_BANK = "NEXT_BANK"
    FOLLOW_UP = "FOLLOW_UP"


class JuryRoutingProviderError(Exception):
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


class JuryRoutingFailed(Exception):
    pass


@dataclass(frozen=True, slots=True)
class JuryRoutingRequest:
    question_text: str
    expected_answer_points: list[str]
    student_answer: str
    focus_type: str
    strictness: int
    interruption_level: str


class JuryRoutingDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    action: JuryAction
    reason_code: str = Field(min_length=3, max_length=100)
    follow_up_question: str | None = Field(None, max_length=1000)


@dataclass(frozen=True, slots=True)
class JuryRoutingResult:
    decision: JuryRoutingDecision
    provider: str
    model: str
    fallback_used: bool
    latency_ms: int
    primary_failure_reason: str | None


class JuryRoutingProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def model(self) -> str: ...

    async def route(self, request: JuryRoutingRequest) -> JuryRoutingDecision: ...


JURY_ROUTING_JSON_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["NEXT_BANK", "FOLLOW_UP"],
        },
        "reason_code": {"type": "string"},
        "follow_up_question": {"type": ["string", "null"]},
    },
    "required": ["action", "reason_code"],
    "additionalProperties": False,
}
