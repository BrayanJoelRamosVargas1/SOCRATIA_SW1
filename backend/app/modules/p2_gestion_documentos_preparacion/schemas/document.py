from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.p2_gestion_documentos_preparacion.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_name: str
    file_type: str
    file_size: int
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime


class ProcessingStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: DocumentStatus
    stage: str
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None


class ProcessingStatusResponse(BaseModel):
    document_id: str
    status: DocumentStatus
    chunk_count: int
    history: list[ProcessingStepResponse]


class DocumentProcessingResponse(BaseModel):
    document_id: str
    status: DocumentStatus
    chunk_count: int
    embedding_model: str
    embedding_dimensions: int
