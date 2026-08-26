from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p2_gestion_documentos_preparacion.exceptions import DocumentNotFoundError
from app.modules.p2_gestion_documentos_preparacion.models.document import Document


class DocumentPolicy:
    """Ownership checks deliberately return 404 to avoid leaking document identifiers."""

    @staticmethod
    def assert_owner(user: User, document: Document | None) -> Document:
        if document is None or document.user_id != user.id:
            raise DocumentNotFoundError
        return document

    can_read = assert_owner
    can_delete = assert_owner
    can_process = assert_owner
