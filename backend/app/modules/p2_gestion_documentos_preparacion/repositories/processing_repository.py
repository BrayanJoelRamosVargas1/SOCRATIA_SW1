from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.modules.p2_gestion_documentos_preparacion.models.document import (
    Document,
    DocumentChunk,
    DocumentProcessing,
    DocumentProcessingJob,
    DocumentStatus,
)


@dataclass(frozen=True, slots=True)
class ChunkInput:
    index: int
    text: str
    start_char: int
    end_char: int


class ProcessingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add_event(
        self,
        *,
        document: Document,
        status: DocumentStatus,
        stage: str,
        started_at: datetime,
        finished_at: datetime | None = None,
        error_message: str | None = None,
    ) -> DocumentProcessing:
        event = DocumentProcessing(
            document=document,
            status=status,
            stage=stage,
            started_at=started_at,
            finished_at=finished_at,
            error_message=error_message,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def get_job(self, document_id: str) -> DocumentProcessingJob | None:
        statement = select(DocumentProcessingJob).where(
            DocumentProcessingJob.document_id == document_id
        )
        return self.db.scalar(statement)

    def create_job(self, document: Document) -> DocumentProcessingJob:
        job = DocumentProcessingJob(document=document, status=DocumentStatus.QUEUED)
        self.db.add(job)
        self.db.flush()
        return job

    def update_job_status(self, job: DocumentProcessingJob, status: DocumentStatus) -> None:
        job.status = status
        self.db.flush()

    def replace_chunks(
        self,
        *,
        document: Document,
        chunks: list[ChunkInput],
    ) -> list[DocumentChunk]:
        self.db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        persisted: list[DocumentChunk] = []
        for chunk in chunks:
            persisted_chunk = DocumentChunk(
                document=document,
                chunk_index=chunk.index,
                content=chunk.text,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
            )
            self.db.add(persisted_chunk)
            persisted.append(persisted_chunk)
        self.db.flush()
        return persisted

    def get_chunks(self, document_id: str) -> list[DocumentChunk]:
        statement = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(self.db.scalars(statement))

    def get_chunk_indices(self, document_id: str) -> list[int]:
        statement = select(DocumentChunk.chunk_index).where(
            DocumentChunk.document_id == document_id
        )
        return list(self.db.scalars(statement))

    def count_chunks(self, document_id: str) -> int:
        statement = (
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )
        return int(self.db.scalar(statement) or 0)
