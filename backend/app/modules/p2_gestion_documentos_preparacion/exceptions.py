"""Domain errors owned by P2."""

from app.core.exceptions import DomainError


class DocumentNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__("Documento no encontrado.", code="document_not_found", status_code=404)


class InvalidDocumentFileError(DomainError):
    def __init__(self, message: str = "El archivo debe ser un PDF o DOCX válido.") -> None:
        super().__init__(message, code="invalid_document_file", status_code=422)


class DocumentTooLargeError(DomainError):
    def __init__(self, max_size_mb: int) -> None:
        super().__init__(
            f"El archivo supera el límite de {max_size_mb} MB.",
            code="document_too_large",
            status_code=413,
        )


class DocumentStorageError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "No fue posible guardar el archivo. Intenta nuevamente.",
            code="document_storage_unavailable",
            status_code=503,
        )


class DocumentAlreadyProcessingError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "El documento ya se esta procesando.",
            code="document_already_processing",
            status_code=409,
        )


class DocumentContentError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "No fue posible extraer texto util del documento.",
            code="document_content_unreadable",
            status_code=422,
        )


class DocumentProcessingUnavailableError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "No fue posible procesar el documento. Intenta nuevamente.",
            code="document_processing_unavailable",
            status_code=503,
        )
