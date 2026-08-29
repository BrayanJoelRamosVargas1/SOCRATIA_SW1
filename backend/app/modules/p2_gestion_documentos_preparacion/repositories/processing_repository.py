from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.modules.p2_gestion_documentos_preparacion.models.document import (
    Document,
    DocumentChunk,
    DocumentProcessing,
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

    def replace_chunks(
        self,
        *,
        document: Document,
        chunks: list[ChunkInput],
        model: str,
        dimensions: int,
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
                vector_id=f"{document.id}:{chunk.index}",
                embedding_model=model,
                embedding_dimensions=dimensions,
            )
            self.db.add(persisted_chunk)
            persisted.append(persisted_chunk)
        self.db.flush()
        return persisted

    def vector_ids(self, document_id: str) -> list[str]:
        statement = (
            select(DocumentChunk.vector_id)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(self.db.scalars(statement))

    def count_chunks(self, document_id: str) -> int:
        statement = select(func.count()).select_from(DocumentChunk).where(
            DocumentChunk.document_id == document_id
        )
        return int(self.db.scalar(statement) or 0)
