from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.integrations.llm import QuestionCategory, QuestionDifficulty
from app.modules.p2_gestion_documentos_preparacion.models.question_bank import (
    QuestionBankStatus,
)


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    question: str
    category: QuestionCategory
    difficulty: QuestionDifficulty


class QuestionBankResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    status: QuestionBankStatus
    provider_used: str
    model_used: str
    fallback_used: bool
    latency_ms: int | None
    created_at: datetime
    updated_at: datetime
    questions: list[QuestionResponse]
