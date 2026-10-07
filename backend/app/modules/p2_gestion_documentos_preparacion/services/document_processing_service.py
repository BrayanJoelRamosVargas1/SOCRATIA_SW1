import hashlib
import logging
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.embeddings import (
    EmbeddingCoordinator,
    EmbeddingDocument,
    EmbeddingError,
    FallbackTriggered,
)
from app.integrations.storage import StorageError, StorageProvider
from app.integrations.vector_db import (
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
    DocumentProcessingJob,
    DocumentStatus,
    EmbeddingProfile,
    ProfileStatus,
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
        embeddings: EmbeddingCoordinator,
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
        if document.status not in (
            DocumentStatus.UPLOADED,
            DocumentStatus.ERROR,
            DocumentStatus.PROCESSED,
        ):
            raise DocumentAlreadyProcessingError

        job = self.processing.get_job(document.id)
        if not job:
            job = self.processing.create_job(document)

        if not job.current_embedding_space:
            initial_provider = self.embeddings.get_initial_provider()
            job.current_embedding_space = initial_provider.embedding_space_id
            self.db.commit()

        current_event = self._start(document, "EXTRACTION", DocumentStatus.EXTRACTING)
        try:
            # Generate fingerprint using content_hash and config versions
            fingerprint_str = f"{document.content_hash}|{self.settings.document_chunk_size_chars}|{self.settings.document_chunk_overlap_chars}|{self.settings.document_extractor_version}|{self.settings.document_normalization_version}|{self.settings.document_chunker_version}"
            fingerprint = hashlib.sha256(fingerprint_str.encode("utf-8")).hexdigest()

            chunk_set = self.processing.get_or_create_chunk_set(
                document=document,
                fingerprint=fingerprint,
                chunk_size_chars=self.settings.document_chunk_size_chars,
                chunk_overlap_chars=self.settings.document_chunk_overlap_chars,
                extractor_version=self.settings.document_extractor_version,
                normalization_version=self.settings.document_normalization_version,
                chunker_version=self.settings.document_chunker_version,
            )

            # Do we need to chunk?
            existing_chunks_count = self.processing.count_chunks(
                document.id
            )  # This currently counts ALL chunks of document, wait we should just check if we have any chunks for this chunk set.
            # Let's see if job is tracking the same chunk_set.
            # If the fingerprint changed, we effectively reset the job tracking for chunks.
            # Resume condition: job tracks this exact chunk_set and profile belongs to it
            # Resume condition: job tracks this exact chunk_set
            if (
                job.chunk_set_id == chunk_set.id
                and job.chunks_total > 0
                and len(chunk_set.chunks) == job.chunks_total
            ):
                # Resume from checkpoint
                logger.info(
                    "Resuming processing for %s from chunk %s/%s",
                    document.id,
                    job.chunks_embedded,
                    job.chunks_total,
                )
                chunks = self.processing.get_chunks(chunk_set.id)
            else:
                logger.info(
                    "Extracting and chunking document %s (fingerprint: %s)",
                    document.id,
                    fingerprint,
                )
                content = self.storage.read(document.storage_key)
                text = self.extractor.extract(file_type=document.file_type, content=content)

                current_event = self._advance(
                    document, current_event, "CHUNKING", DocumentStatus.CHUNKING
                )
                raw_chunks = self.chunker.split(text)
                if not raw_chunks or len(raw_chunks) > self.settings.document_max_chunks:
                    raise TextExtractionError("Document chunk count is outside accepted limits")

                chunk_inputs = [
                    ChunkInput(
                        index=chunk.index,
                        text=chunk.text,
                        start_char=chunk.start_char,
                        end_char=chunk.end_char,
                    )
                    for chunk in raw_chunks
                ]
                chunks = self.processing.replace_chunks(
                    document=document,
                    chunk_set=chunk_set,
                    chunks=chunk_inputs,
                )

                job.chunk_set_id = chunk_set.id
                job.chunks_total = len(chunks)
                job.chunks_embedded = 0
                job.profile_id = None
                self.db.commit()

            current_event = self._advance(
                document, current_event, "EMBEDDING", DocumentStatus.EMBEDDING
            )

            # --- EMBEDDING LOOP WITH FALLBACK ---
            # We determine the initial active provider based on current_embedding_space
            active_provider = next(
                (
                    p
                    for p in self.embeddings.providers
                    if p.embedding_space_id == job.current_embedding_space and p.is_available
                ),
                self.embeddings.get_initial_provider(),
            )

            while True:
                # Ensure staging profile exists for current space AND current chunk_set
                profile = next(
                    (
                        p
                        for p in document.embedding_profiles
                        if p.embedding_space_id == job.current_embedding_space
                        and p.chunk_set_id == chunk_set.id
                    ),
                    None,
                )
                if not profile:
                    # Depending on provider dimension, choose Pinecone index.
                    vector_index = (
                        self.settings.pinecone_index_name
                        if active_provider.dimensions == 768
                        else "socratia-d1024-cosine"
                    )

                    profile = EmbeddingProfile(
                        document_id=document.id,
                        chunk_set_id=chunk_set.id,
                        status=ProfileStatus.STAGING,
                        embedding_space_id=job.current_embedding_space,
                        provider=active_provider.provider_id,
                        model=active_provider.model,
                        dimension=active_provider.dimensions,
                        vector_index=vector_index,
                        vector_namespace="",  # Will be set once we have profile ID
                    )
                    self.db.add(profile)
                    self.db.flush()
                    profile.vector_namespace = f"d-{document.id}-p-{profile.id}"
                    document.embedding_profiles.append(profile)
                    self.db.commit()

                if job.profile_id != profile.id:
                    job.profile_id = profile.id
                    job.chunks_embedded = 0  # reset embedding progress if profile changed
                    self.db.commit()

                # Skip already embedded chunks
                chunks_to_embed = chunks[job.chunks_embedded :]
                embedding_documents = [
                    EmbeddingDocument(title=document.original_name, text=chunk.content)
                    for chunk in chunks_to_embed
                ]

                namespace = profile.vector_namespace
                batch_offset = 0
                advanced_to_indexing = False

                try:
                    # Provide the active_provider to the coordinator
                    for batch_embeddings in self.embeddings.embed_documents_with_fallback(
                        embedding_documents, active_provider
                    ):
                        if not advanced_to_indexing:
                            current_event = self._advance(
                                document, current_event, "VECTOR_STORE", DocumentStatus.INDEXING
                            )
                            advanced_to_indexing = True

                        batch_chunks = chunks_to_embed[
                            batch_offset : batch_offset + len(batch_embeddings)
                        ]

                        from app.modules.p2_gestion_documentos_preparacion.models.vector_store import (
                            EmbeddingProfileStoreSync,
                            VectorSyncOutbox,
                        )

                        # Ensure sync trackers exist
                        for store_name in ["pinecone", "pgvector"]:
                            sync = (
                                self.db.query(EmbeddingProfileStoreSync)
                                .filter_by(profile_id=profile.id, store_name=store_name)
                                .first()
                            )
                            if not sync:
                                sync = EmbeddingProfileStoreSync(
                                    profile_id=profile.id,
                                    store_name=store_name,
                                    status="SYNCING",
                                    vectors_expected=job.chunks_total,
                                )
                                self.db.add(sync)
                        self.db.flush()

                        for chunk, embedding in zip(batch_chunks, batch_embeddings, strict=True):
                            outbox = VectorSyncOutbox(
                                profile_id=profile.id,
                                chunk_id=chunk.id,
                                dimension=active_provider.dimensions,
                                operation="UPSERT",
                            )
                            self.db.add(outbox)

                        # Insert vectors using raw SQL to cast correctly
                        table_name = (
                            "vector_embeddings_768"
                            if active_provider.dimensions == 768
                            else "vector_embeddings_1024"
                        )
                        import uuid

                        from sqlalchemy import text

                        sql = text(f"""
                            INSERT INTO {table_name} 
                            (id, profile_id, chunk_id, document_id, user_id, embedding_space_id, embedding)
                            VALUES (:id, :profile_id, :chunk_id, :doc_id, :user_id, :space_id, CAST(:embedding AS vector))
                        """)

                        insert_params = []
                        for chunk, embedding in zip(batch_chunks, batch_embeddings, strict=True):
                            insert_params.append(
                                {
                                    "id": str(uuid.uuid4()),
                                    "profile_id": profile.id,
                                    "chunk_id": chunk.id,
                                    "doc_id": document.id,
                                    "user_id": user.id,
                                    "space_id": job.current_embedding_space,
                                    "embedding": "[" + ",".join(map(str, embedding)) + "]",
                                }
                            )

                        if insert_params:
                            self.db.execute(sql, insert_params)

                        pg_sync = (
                            self.db.query(EmbeddingProfileStoreSync)
                            .filter_by(profile_id=profile.id, store_name="pgvector")
                            .first()
                        )
                        if pg_sync:
                            pg_sync.vectors_synced = job.chunks_embedded + len(batch_embeddings)
                            if pg_sync.vectors_synced >= pg_sync.vectors_expected:
                                pg_sync.status = "SYNCED"

                        batch_offset += len(batch_embeddings)
                        job.chunks_embedded = job.chunks_embedded + len(batch_embeddings)
                        self.db.commit()

                    # Successfully embedded all chunks! Break the fallback loop

                    # Atomic promotion
                    profile.status = ProfileStatus.ACTIVE
                    profile.completed_at = datetime.now(UTC)
                    document.active_embedding_profile_id = profile.id

                    # Retire old active profiles if any
                    for p in document.embedding_profiles:
                        if p.id != profile.id and p.status in (
                            ProfileStatus.READY,
                            ProfileStatus.ACTIVE,
                        ):
                            p.status = ProfileStatus.RETIRED

                    self.db.commit()
                    break

                except FallbackTriggered as exc:
                    logger.warning(
                        "Fallback triggered! Type: %s, Next Provider: %s",
                        exc.fallback_type,
                        exc.next_provider.provider_id,
                    )
                    active_provider = exc.next_provider

                    if exc.fallback_type == "SPACE_CHANGE":
                        # Mark current profile as failed because we need a new space
                        profile.status = ProfileStatus.FAILED
                        job.current_embedding_space = active_provider.embedding_space_id
                        job.chunks_embedded = 0  # Restart chunk progress
                    else:
                        # EXECUTOR_CHANGE: Same space, just a different provider.
                        # Do not overwrite profile.provider here. The profile defines the embedding space,
                        # while telemetry tracks which executor processed each chunk.
                        pass

                    job.attempt += 1
                    self.db.commit()

                    # Loop restarts, will either create a new profile (if SPACE_CHANGE) and restart from chunk 0,
                    # or reuse the existing STAGING profile (if EXECUTOR_CHANGE) and resume chunks.

            self._finish(document, current_event, job)
            return DocumentProcessingResponse(
                document_id=document.id,
                status=document.status,
                chunk_count=len(chunks),
                embedding_model=active_provider.model,
                embedding_dimensions=active_provider.dimensions,
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

    def _start(self, document: Document, stage: str, status: DocumentStatus) -> DocumentProcessing:
        document.status = status
        event = self.processing.add_event(
            document=document,
            status=status,
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
        status: DocumentStatus,
    ) -> DocumentProcessing:
        event.finished_at = datetime.now(UTC)
        document.status = status
        next_event = self.processing.add_event(
            document=document,
            status=status,
            stage=next_stage,
            started_at=datetime.now(UTC),
        )
        self.db.commit()
        return next_event

    def _finish(
        self, document: Document, event: DocumentProcessing, job: DocumentProcessingJob
    ) -> None:
        now = datetime.now(UTC)
        event.finished_at = now
        document.status = DocumentStatus.PROCESSED
        job.status = DocumentStatus.PROCESSED
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
        job = self.processing.get_job(document_id)
        if document is None or event is None:
            logger.error("Could not persist processing failure for document %s", document_id)
            return
        now = datetime.now(UTC)
        document.status = DocumentStatus.ERROR
        if job:
            job.status = DocumentStatus.ERROR
            job.error_message = message
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
