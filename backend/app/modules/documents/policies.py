from app.modules.documents.exceptions import DocumentNotFoundError
from app.modules.documents.models import Document
from app.modules.users.models import User


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

