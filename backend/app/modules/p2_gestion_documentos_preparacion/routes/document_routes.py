from typing import Annotated

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.integrations.embeddings.base import EmbeddingProvider
from app.integrations.embeddings.dependencies import get_embedding_provider
from app.integrations.storage.base import StorageProvider
from app.integrations.storage.dependencies import get_storage_provider
from app.integrations.vector_db.base import VectorStoreProvider
from app.integrations.vector_db.dependencies import get_vector_store_provider
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import CurrentUser
from app.modules.p2_gestion_documentos_preparacion.schemas.document import (
    DocumentProcessingResponse,
    DocumentResponse,
    ProcessingStatusResponse,
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


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: Annotated[UploadFile, File(description="PDF o DOCX de hasta 20 MB")],
    current_user: CurrentUser,
    db: Database,
    storage_provider: Storage,
) -> DocumentResponse:
    document = DocumentService(db, storage_provider).upload(current_user, file)
    return DocumentResponse.model_validate(document)


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
