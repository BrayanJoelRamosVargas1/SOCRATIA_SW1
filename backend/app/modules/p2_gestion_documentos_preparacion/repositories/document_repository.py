from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.p2_gestion_documentos_preparacion.models.document import (
    Document,
    DocumentStatus,
)


class DocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        document_id: str,
        user_id: str,
        original_name: str,
        file_type: str,
        file_size: int,
        storage_key: str,
    ) -> Document:
        document = Document(
            id=document_id,
            user_id=user_id,
            original_name=original_name,
            file_type=file_type,
            file_size=file_size,
            storage_key=storage_key,
            status=DocumentStatus.UPLOADED,
        )
        self.db.add(document)
        self.db.flush()
        return document

    def list_by_owner(self, user_id: str) -> list[Document]:
        statement = (
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc(), Document.id.desc())
        )
        return list(self.db.scalars(statement).unique())

    def get_by_id(self, document_id: str) -> Document | None:
        return self.db.get(Document, document_id)

    def get_by_id_for_update(self, document_id: str) -> Document | None:
        statement = select(Document).where(Document.id == document_id).with_for_update()
        return self.db.scalars(statement).unique().one_or_none()

    def delete(self, document: Document) -> None:
        self.db.delete(document)
