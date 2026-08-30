from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.integrations.embeddings.base import EmbeddingProvider
from app.integrations.embeddings.dependencies import get_embedding_provider
from app.integrations.llm.dependencies import get_question_generation_router
from app.integrations.llm.router import QuestionGenerationRouter
from app.integrations.vector_db.base import VectorStoreProvider
from app.integrations.vector_db.dependencies import get_vector_store_provider
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import CurrentUser
from app.modules.p2_gestion_documentos_preparacion.schemas.question_bank import (
    QuestionBankResponse,
)
from app.modules.p2_gestion_documentos_preparacion.services.question_bank_service import (
    QuestionBankService,
)

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]
Embeddings = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
VectorStore = Annotated[VectorStoreProvider, Depends(get_vector_store_provider)]
GenerationRouter = Annotated[
    QuestionGenerationRouter,
    Depends(get_question_generation_router),
]


@router.post("/{document_id}/questions/generate", response_model=QuestionBankResponse)
def generate_question_bank(
    document_id: str,
    current_user: CurrentUser,
    db: Database,
    embedding_provider: Embeddings,
    vector_store: VectorStore,
    generation_router: GenerationRouter,
) -> QuestionBankResponse:
    bank = QuestionBankService(
        db=db,
        embeddings=embedding_provider,
        vectors=vector_store,
        generation_router=generation_router,
    ).generate(current_user, document_id)
    return QuestionBankResponse.model_validate(bank)


@router.get("/{document_id}/questions", response_model=QuestionBankResponse)
def get_question_bank(
    document_id: str,
    current_user: CurrentUser,
    db: Database,
    embedding_provider: Embeddings,
    vector_store: VectorStore,
    generation_router: GenerationRouter,
) -> QuestionBankResponse:
    bank = QuestionBankService(
        db=db,
        embeddings=embedding_provider,
        vectors=vector_store,
        generation_router=generation_router,
    ).get(current_user, document_id)
    return QuestionBankResponse.model_validate(bank)
