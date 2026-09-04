from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.p3_gestion_simulacion.models import (
    SimulationQuestionSource,
    SimulationStatus,
    SimulationTurnInputMode,
    SimulationTurnSpeaker,
    SimulationTurnState,
    SimulationTurnType,
)


class SessionQuestionResponse(BaseModel):
    id: str
    position: int
    text: str
    source: SimulationQuestionSource


class SessionTurnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sequence: int
    speaker: SimulationTurnSpeaker
    turn_type: SimulationTurnType
    input_mode: SimulationTurnInputMode
    simulation_question_id: str | None
    question_source: SimulationQuestionSource | None
    content: str
    created_at: datetime


class SessionSnapshot(BaseModel):
    simulation_id: str
    status: SimulationStatus
    turn_state: SimulationTurnState
    current_question: SessionQuestionResponse | None
    answered_questions: int
    total_questions: int
    last_sequence: int
    questions_exhausted: bool
    started_at: datetime
    transcript: list[SessionTurnResponse]


class AnswerSubmitPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    content: str = Field(min_length=1, max_length=10_000)


class AnswerSubmitMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["answer.submit"]
    message_id: UUID
    payload: AnswerSubmitPayload


class AnswerAccepted(BaseModel):
    message_id: str
    answer_sequence: int
    duplicate: bool


class VoiceUtteranceStartPayload(BaseModel):
    mime_type: str = Field(min_length=1, max_length=100)


class VoiceUtteranceStartMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["voice.utterance.start"]
    message_id: UUID
    payload: VoiceUtteranceStartPayload


class VoiceUtteranceEndMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["voice.utterance.end"]
    message_id: UUID


class ServerEventState(BaseModel):
    type: Literal["voice.listening", "voice.transcribing", "jury.thinking", "jury.speaking", "jury.finished", "error"]
    message: str | None = None
