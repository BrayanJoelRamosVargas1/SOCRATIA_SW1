"""SQLAlchemy models owned by P2."""

from app.modules.p2_gestion_documentos_preparacion.models.document import (
    Document,
    DocumentChunk,
    DocumentProcessing,
    DocumentStatus,
)
from app.modules.p2_gestion_documentos_preparacion.models.presentation_material import (
    PresentationMaterial,
    PresentationMaterialStatus,
    PresentationSlide,
)
from app.modules.p2_gestion_documentos_preparacion.models.question_bank import (
    Question,
    QuestionBank,
    QuestionBankStatus,
)

__all__ = [
    "Document",
    "DocumentChunk",
    "DocumentProcessing",
    "DocumentStatus",
    "PresentationMaterial",
    "PresentationMaterialStatus",
    "PresentationSlide",
    "Question",
    "QuestionBank",
    "QuestionBankStatus",
]
