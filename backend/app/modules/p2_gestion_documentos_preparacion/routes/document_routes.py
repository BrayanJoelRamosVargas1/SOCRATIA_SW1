from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.integrations.embeddings.base import EmbeddingProvider
from app.integrations.embeddings.dependencies import get_embedding_provider
from app.integrations.retrieval.base import FallbackReason, RetrievalMode
from app.integrations.retrieval.dependencies import get_retrieval_router
from app.integrations.retrieval.router import RetrievalRouter
from app.integrations.storage.base import StorageProvider
from app.integrations.storage.dependencies import get_storage_provider
from app.integrations.vector_db.base import VectorStoreProvider
from app.integrations.vector_db.dependencies import get_vector_store_provider
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import CurrentUser
from app.modules.p2_gestion_documentos_preparacion.models.document import (
    DocumentChunk,
    DocumentStatus,
)
from app.modules.p2_gestion_documentos_preparacion.schemas.document import (
    DocumentProcessingResponse,
    DocumentResponse,
    ProcessingStatusResponse,
)
from app.modules.p2_gestion_documentos_preparacion.schemas.search import (
    DocumentSearchMatch,
    DocumentSearchRequest,
    DocumentSearchResponse,
)
from app.modules.p2_gestion_documentos_preparacion.services.document_processing_service import (
    DocumentProcessingService,
)
from app.modules.p2_gestion_documentos_preparacion.services.document_service import (
    DocumentService,
)

router = APIRouter()
Storage = Annotated[StorageProvider, Depends(get_storage_provider)]
Embeddings = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
VectorStore = Annotated[VectorStoreProvider, Depends(get_vector_store_provider)]
Database = Annotated[Session, Depends(get_db)]
Retrieval = Annotated[RetrievalRouter, Depends(get_retrieval_router)]


@router.get("/capabilities")
def document_capabilities(current_user: CurrentUser) -> dict[str, int]:
    from app.core.config import get_settings
    return {"max_document_size_mb": get_settings().max_document_size_mb}


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: Annotated[UploadFile, File(description="PDF o DOCX; límite disponible en /documents/capabilities")],
    current_user: CurrentUser,
    db: Database,
    storage_provider: Storage,
) -> DocumentResponse:
    document = DocumentService(db, storage_provider).upload(current_user, file)
    return DocumentResponse.model_validate(document)


@router.get("/readiness")
def document_readiness(current_user: CurrentUser, db: Database) -> dict[str, list[str]]:
    """One owner-scoped query instead of downloading every question bank."""
    from sqlalchemy import select

    from app.modules.p2_gestion_documentos_preparacion.models.document import (
        Document,
        DocumentStatus,
    )
    from app.modules.p2_gestion_documentos_preparacion.models.question_bank import (
        QuestionBank,
        QuestionBankStatus,
    )
    ids = db.scalars(select(QuestionBank.document_id).join(Document, Document.id == QuestionBank.document_id).where(
        Document.user_id == current_user.id, QuestionBank.user_id == current_user.id,
        Document.status == DocumentStatus.PROCESSED, QuestionBank.status == QuestionBankStatus.READY,
    )).all()
    return {"ready_document_ids": list(ids)}


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    current_user: CurrentUser,
    db: Database,
    storage_provider: Storage,
) -> list[DocumentResponse]:
    documents = DocumentService(db, storage_provider).list_for(current_user)
    return [DocumentResponse.model_validate(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    current_user: CurrentUser,
    db: Database,
    storage_provider: Storage,
) -> DocumentResponse:
    document = DocumentService(db, storage_provider).get_for(current_user, document_id)
    return DocumentResponse.model_validate(document)


@router.post("/{document_id}/search", response_model=DocumentSearchResponse)
def search_document(
    document_id: str, payload: DocumentSearchRequest, current_user: CurrentUser,
    db: Database, storage_provider: Storage, retrieval: Retrieval,
) -> DocumentSearchResponse:
    # Authorize before any inference or vector access.
    document = DocumentService(db, storage_provider).get_for(current_user, document_id)
    if document.status != DocumentStatus.PROCESSED:
        raise HTTPException(409, "Procesa el documento antes de buscar en su contenido.")
    results, reason = retrieval.retrieve_for_document(document, current_user.id, payload.query, 3)
    profile = next((p for p in document.embedding_profiles
                    if p.id == document.active_embedding_profile_id), None)
    degraded = reason != FallbackReason.NONE or any(
        item.retrieval_mode == RetrievalMode.LEXICAL_FALLBACK for item in results
    )
    engine = "text" if degraded else "semantic"
    if not degraded and profile and profile.provider == "qwen_local":
        engine = "qwen_local"
    # Fetch canonical excerpts scoped to this owner's document, never trust vector payload text.
    chunks = {c.id: c for c in db.scalars(select(DocumentChunk).where(
        DocumentChunk.document_id == document.id,
        DocumentChunk.id.in_([r.chunk_id for r in results]),
        DocumentChunk.chunk_set_id == profile.chunk_set_id if profile else True,
    )).all()}
    return DocumentSearchResponse(
        engine=engine, model=profile.model if profile and not degraded else None,
        degraded=degraded, matches=[DocumentSearchMatch(
            fragment=chunks[r.chunk_id].chunk_index + 1,
            excerpt=chunks[r.chunk_id].content[:900],
        ) for r in results if r.chunk_id in chunks],
    )


@router.get("/{document_id}/status", response_model=ProcessingStatusResponse)
def get_document_status(
    document_id: str,
    current_user: CurrentUser,
    db: Database,
    storage_provider: Storage,
) -> ProcessingStatusResponse:
    return DocumentService(db, storage_provider).get_status_for(current_user, document_id)


@router.post("/{document_id}/process", response_model=DocumentProcessingResponse)
def process_document(
    document_id: str,
    current_user: CurrentUser,
    db: Database,
    storage_provider: Storage,
    embedding_provider: Embeddings,
    vector_store: VectorStore,
) -> DocumentProcessingResponse:
    return DocumentProcessingService(
        db,
        storage_provider,
        embedding_provider,
        vector_store,
    ).process(current_user, document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    current_user: CurrentUser,
    db: Database,
    storage_provider: Storage,
    vector_store: VectorStore,
) -> Response:
    DocumentService(db, storage_provider, vector_store).delete_for(current_user, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
