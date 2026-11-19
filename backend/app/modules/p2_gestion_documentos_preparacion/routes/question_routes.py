from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.integrations.llm.dependencies import get_question_generation_router
from app.integrations.llm.router import QuestionGenerationRouter
from app.integrations.retrieval.dependencies import get_retrieval_router
from app.integrations.retrieval.router import RetrievalRouter
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import CurrentUser
from app.modules.p2_gestion_documentos_preparacion.schemas.question_bank import (
    QuestionBankResponse,
)
from app.modules.p2_gestion_documentos_preparacion.services.question_bank_service import (
    QuestionBankService,
)

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]
Retrieval = Annotated[RetrievalRouter, Depends(get_retrieval_router)]
GenerationRouter = Annotated[
    QuestionGenerationRouter,
    Depends(get_question_generation_router),
]


@router.get("/{document_id}/questions/export")
def download_questions(document_id: str, current_user: CurrentUser, db: Database) -> Response:
    from app.modules.p2_gestion_documentos_preparacion.repositories.document_repository import DocumentRepository
    from app.modules.p2_gestion_documentos_preparacion.repositories.question_bank_repository import QuestionBankRepository
    from app.modules.p2_gestion_documentos_preparacion.policies.document_policy import DocumentPolicy
    from app.modules.p2_gestion_documentos_preparacion.exceptions import QuestionBankNotFoundError
    from app.modules.p2_gestion_documentos_preparacion.services.question_export import export_questions
    document = DocumentPolicy.can_read(current_user, DocumentRepository(db).get_by_id(document_id))
    bank = QuestionBankRepository(db).get_ready_by_document(document.id)
    if bank is None:
        raise QuestionBankNotFoundError
    return Response(export_questions(bank, document.original_name), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="socratia-preguntas.pdf"',
                             "Cache-Control": "private, no-store"})


@router.post("/{document_id}/questions/generate", response_model=QuestionBankResponse)
def generate_question_bank(
    document_id: str,
    current_user: CurrentUser,
    db: Database,
    retrieval_router: Retrieval,
    generation_router: GenerationRouter,
) -> QuestionBankResponse:
    bank = QuestionBankService(
        db=db,
        retrieval_router=retrieval_router,
        generation_router=generation_router,
    ).generate(current_user, document_id)
    return QuestionBankResponse.model_validate(bank)


@router.get("/{document_id}/questions", response_model=QuestionBankResponse)
def get_question_bank(
    document_id: str,
    current_user: CurrentUser,
    db: Database,
    retrieval_router: Retrieval,
    generation_router: GenerationRouter,
) -> QuestionBankResponse:
    bank = QuestionBankService(
        db=db,
        retrieval_router=retrieval_router,
        generation_router=generation_router,
    ).get(current_user, document_id)
    return QuestionBankResponse.model_validate(bank)
