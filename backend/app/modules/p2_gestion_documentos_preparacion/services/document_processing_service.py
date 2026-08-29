import logging
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.embeddings import EmbeddingDocument, EmbeddingError, EmbeddingProvider
from app.integrations.storage import StorageError, StorageProvider
from app.integrations.vector_db import (
    VectorRecord,
    VectorStoreError,
    VectorStoreProvider,
)
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.exceptions import (
    DocumentAlreadyProcessingError,
    DocumentContentError,
    DocumentProcessingUnavailableError,
    DocumentStorageError,
)
from app.modules.p2_gestion_documentos_preparacion.models.document import (
    Document,
    DocumentProcessing,
    DocumentStatus,
)
from app.modules.p2_gestion_documentos_preparacion.policies.document_policy import DocumentPolicy
from app.modules.p2_gestion_documentos_preparacion.repositories.document_repository import (
    DocumentRepository,
)
from app.modules.p2_gestion_documentos_preparacion.repositories.processing_repository import (
    ChunkInput,
    ProcessingRepository,
)
from app.modules.p2_gestion_documentos_preparacion.schemas.document import (
    DocumentProcessingResponse,
)
from app.modules.p2_gestion_documentos_preparacion.services.chunking import ChunkingService
from app.modules.p2_gestion_documentos_preparacion.services.text_extraction import (
    TextExtractionError,
    TextExtractionService,
)

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    def __init__(
        self,
        db: Session,
        storage: StorageProvider,
        embeddings: EmbeddingProvider,
        vectors: VectorStoreProvider,
    ) -> None:
        self.db = db
        self.storage = storage
        self.embeddings = embeddings
        self.vectors = vectors
        self.documents = DocumentRepository(db)
        self.processing = ProcessingRepository(db)
        self.settings = get_settings()
        self.extractor = TextExtractionService()
        self.chunker = ChunkingService(
            max_chars=self.settings.document_chunk_size_chars,
            overlap_chars=self.settings.document_chunk_overlap_chars,
        )

    def process(self, user: User, document_id: str) -> DocumentProcessingResponse:
        document = DocumentPolicy.can_read(
            user,
            self.documents.get_by_id_for_update(document_id),
        )
        if document.status == DocumentStatus.PROCESSING:
            raise DocumentAlreadyProcessingError

        old_vector_ids = self.processing.vector_ids(document.id)
        current_event = self._start(document, "EXTRACTION")
        try:
            content = self.storage.read(document.storage_key)
            text = self.extractor.extract(file_type=document.file_type, content=content)

            current_event = self._advance(document, current_event, "CHUNKING")
            chunks = self.chunker.split(text)
            if not chunks or len(chunks) > self.settings.document_max_chunks:
                raise TextExtractionError("Document chunk count is outside accepted limits")

            current_event = self._advance(document, current_event, "EMBEDDING")
            embedding_documents = [
                EmbeddingDocument(title=document.original_name, text=chunk.text)
                for chunk in chunks
            ]
            embeddings = self.embeddings.embed_documents(embedding_documents)
            if len(embeddings) != len(chunks):
                raise EmbeddingError("Embedding count does not match chunk count")

            current_event = self._advance(document, current_event, "VECTOR_STORE")
            namespace = self._namespace(user.id)
            records = [
                VectorRecord(
                    id=f"{document.id}:{chunk.index}",
                    values=embedding,
                    metadata={
                        "user_id": user.id,
                        "document_id": document.id,
                        "document_name": document.original_name,
                        "chunk_index": chunk.index,
                        "text": chunk.text,
                    },
                )
                for chunk, embedding in zip(chunks, embeddings, strict=True)
            ]
            self.vectors.upsert(namespace=namespace, records=records)
            new_vector_ids = {record.id for record in records}
            obsolete_vector_ids = [
                vector_id for vector_id in old_vector_ids if vector_id not in new_vector_ids
            ]
            self.vectors.delete(namespace=namespace, ids=obsolete_vector_ids)

            chunk_inputs = [
                ChunkInput(
                    index=chunk.index,
                    text=chunk.text,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                )
                for chunk in chunks
            ]
            self.processing.replace_chunks(
                document=document,
                chunks=chunk_inputs,
                model=self.embeddings.model,
                dimensions=self.embeddings.dimensions,
            )
            self._finish(document, current_event)
            return DocumentProcessingResponse(
                document_id=document.id,
                status=document.status,
                chunk_count=len(chunks),
                embedding_model=self.embeddings.model,
                embedding_dimensions=self.embeddings.dimensions,
            )
        except TextExtractionError:
            self._fail(document.id, current_event.id, "Document text could not be extracted")
            raise DocumentContentError from None
        except StorageError:
            self._fail(document.id, current_event.id, "Stored document could not be read")
            raise DocumentStorageError from None
        except (EmbeddingError, VectorStoreError):
            logger.exception("External provider failed while processing document %s", document.id)
            self._fail(document.id, current_event.id, "External processing provider failed")
            raise DocumentProcessingUnavailableError from None
        except SQLAlchemyError:
            logger.exception("Database failed while processing document %s", document.id)
            self._fail(document.id, current_event.id, "Processing persistence failed")
            raise DocumentProcessingUnavailableError from None

    def _start(self, document: Document, stage: str) -> DocumentProcessing:
        document.status = DocumentStatus.PROCESSING
        event = self.processing.add_event(
            document=document,
            status=DocumentStatus.PROCESSING,
            stage=stage,
            started_at=datetime.now(UTC),
        )
        self.db.commit()
        return event

    def _advance(
        self,
        document: Document,
        event: DocumentProcessing,
        next_stage: str,
    ) -> DocumentProcessing:
        event.finished_at = datetime.now(UTC)
        next_event = self.processing.add_event(
            document=document,
            status=DocumentStatus.PROCESSING,
            stage=next_stage,
            started_at=datetime.now(UTC),
        )
        self.db.commit()
        return next_event

    def _finish(self, document: Document, event: DocumentProcessing) -> None:
        now = datetime.now(UTC)
        event.finished_at = now
        document.status = DocumentStatus.PROCESSED
        self.processing.add_event(
            document=document,
            status=DocumentStatus.PROCESSED,
            stage="COMPLETE",
            started_at=now,
            finished_at=now,
        )
        self.db.commit()

    def _fail(self, document_id: str, event_id: str, message: str) -> None:
        self.db.rollback()
        document = self.documents.get_by_id(document_id)
        event = self.db.get(DocumentProcessing, event_id)
        if document is None or event is None:
            logger.error("Could not persist processing failure for document %s", document_id)
            return
        now = datetime.now(UTC)
        document.status = DocumentStatus.ERROR
        event.status = DocumentStatus.ERROR
        event.finished_at = now
        event.error_message = message
        try:
            self.db.commit()
        except SQLAlchemyError:
            self.db.rollback()
            logger.exception("Could not persist processing failure for document %s", document_id)

    def _namespace(self, user_id: str) -> str:
        return f"{self.settings.pinecone_namespace_prefix}-{user_id}"
