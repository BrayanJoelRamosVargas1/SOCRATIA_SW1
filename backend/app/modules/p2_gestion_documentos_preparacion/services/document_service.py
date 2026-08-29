import uuid
import zipfile
from datetime import UTC, datetime

from fastapi import UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.integrations.storage import StorageError, StorageProvider
from app.integrations.vector_db import VectorStoreError, VectorStoreProvider
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.exceptions import (
    DocumentAlreadyProcessingError,
    DocumentProcessingUnavailableError,
    DocumentStorageError,
    DocumentTooLargeError,
    InvalidDocumentFileError,
)
from app.modules.p2_gestion_documentos_preparacion.models.document import (
    Document,
    DocumentStatus,
)
from app.modules.p2_gestion_documentos_preparacion.policies.document_policy import DocumentPolicy
from app.modules.p2_gestion_documentos_preparacion.repositories.document_repository import (
    DocumentRepository,
)
from app.modules.p2_gestion_documentos_preparacion.repositories.processing_repository import (
    ProcessingRepository,
)
from app.modules.p2_gestion_documentos_preparacion.schemas.document import (
    ProcessingStatusResponse,
)

ALLOWED_DOCUMENTS = {
    ".pdf": {
        "file_type": "PDF",
        "content_types": {"application/pdf", "application/octet-stream"},
    },
    ".docx": {
        "file_type": "DOCX",
        "content_types": {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/octet-stream",
        },
    },
}


class DocumentService:
    def __init__(
        self,
        db: Session,
        storage: StorageProvider,
        vectors: VectorStoreProvider | None = None,
    ) -> None:
        self.db = db
        self.storage = storage
        self.vectors = vectors
        self.documents = DocumentRepository(db)
        self.processing = ProcessingRepository(db)
        self.settings = get_settings()

    def upload(self, user: User, file: UploadFile) -> Document:
        original_name, extension, file_type, size = self._validate(file)
        document_id = str(uuid.uuid4())
        storage_key = (
            f"users/{user.id}/documents/{document_id}/{document_id}{extension}"
        )

        try:
            persisted_size = self.storage.save(storage_key, file.file)
        except StorageError as exc:
            raise DocumentStorageError from exc
        if persisted_size != size:
            self.storage.delete(storage_key)
            raise DocumentStorageError

        try:
            document = self.documents.create(
                document_id=document_id,
                user_id=user.id,
                original_name=original_name,
                file_type=file_type,
                file_size=size,
                storage_key=storage_key,
            )
            now = datetime.now(UTC)
            self.processing.add_event(
                document=document,
                status=DocumentStatus.UPLOADED,
                stage="UPLOAD",
                started_at=now,
                finished_at=now,
            )
            self.db.commit()
            self.db.refresh(document)
            return document
        except SQLAlchemyError:
            self.db.rollback()
            try:
                self.storage.delete(storage_key)
            except StorageError:
                pass
            raise

    def list_for(self, user: User) -> list[Document]:
        return self.documents.list_by_owner(user.id)

    def get_for(self, user: User, document_id: str) -> Document:
        return DocumentPolicy.can_read(user, self.documents.get_by_id(document_id))

    def get_status_for(self, user: User, document_id: str) -> ProcessingStatusResponse:
        document = self.get_for(user, document_id)
        return ProcessingStatusResponse(
            document_id=document.id,
            status=document.status,
            chunk_count=self.processing.count_chunks(document.id),
            history=list(document.processing_history),
        )

    def delete_for(self, user: User, document_id: str) -> None:
        document = DocumentPolicy.can_delete(user, self.documents.get_by_id(document_id))
        if document.status == DocumentStatus.PROCESSING:
            raise DocumentAlreadyProcessingError
        vector_ids = self.processing.vector_ids(document.id)
        if vector_ids:
            if self.vectors is None:
                raise DocumentProcessingUnavailableError
            try:
                self.vectors.delete(
                    namespace=f"{self.settings.pinecone_namespace_prefix}-{user.id}",
                    ids=vector_ids,
                )
            except VectorStoreError as exc:
                raise DocumentProcessingUnavailableError from exc
        try:
            self.storage.delete(document.storage_key)
        except StorageError as exc:
            raise DocumentStorageError from exc
        self.documents.delete(document)
        self.db.commit()

    def _validate(self, file: UploadFile) -> tuple[str, str, str, int]:
        original_name = self._safe_name(file.filename)
        extension = "." + original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
        allowed = ALLOWED_DOCUMENTS.get(extension)
        if allowed is None:
            raise InvalidDocumentFileError

        content_type = (file.content_type or "").split(";", 1)[0].lower()
        if content_type not in allowed["content_types"]:
            raise InvalidDocumentFileError("El tipo MIME no coincide con un PDF o DOCX permitido.")

        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        if size <= 0:
            raise InvalidDocumentFileError("El archivo está vacío.")
        if size > self.settings.max_document_size_bytes:
            raise DocumentTooLargeError(self.settings.max_document_size_mb)

        if extension == ".pdf":
            if file.file.read(5) != b"%PDF-":
                file.file.seek(0)
                raise InvalidDocumentFileError("El contenido no corresponde a un PDF válido.")
        else:
            try:
                with zipfile.ZipFile(file.file) as archive:
                    names = set(archive.namelist())
                    uncompressed_size = sum(info.file_size for info in archive.infolist())
                    if uncompressed_size > self.settings.max_document_size_bytes * 5:
                        raise InvalidDocumentFileError(
                            "El contenido descomprimido del DOCX supera el limite permitido."
                        )
                    if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                        raise InvalidDocumentFileError(
                            "El contenido no corresponde a un DOCX válido."
                        )
            except zipfile.BadZipFile as exc:
                raise InvalidDocumentFileError(
                    "El contenido no corresponde a un DOCX válido."
                ) from exc
        file.file.seek(0)
        return original_name, extension, str(allowed["file_type"]), size

    @staticmethod
    def _safe_name(filename: str | None) -> str:
        if not filename:
            raise InvalidDocumentFileError("El archivo debe tener un nombre.")
        safe_name = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
        if not safe_name or safe_name in {".", ".."} or len(safe_name) > 255:
            raise InvalidDocumentFileError("El nombre del archivo no es válido.")
        return safe_name
