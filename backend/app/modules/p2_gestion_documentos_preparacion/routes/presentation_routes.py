from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.integrations.embeddings.base import EmbeddingProvider
from app.integrations.embeddings.dependencies import get_embedding_provider
from app.integrations.llm.dependencies import get_presentation_generation_router
from app.integrations.llm.presentation_router import PresentationGenerationRouter
from app.integrations.vector_db.base import VectorStoreProvider
from app.integrations.vector_db.dependencies import get_vector_store_provider
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import CurrentUser
from app.modules.p2_gestion_documentos_preparacion.schemas.presentation_material import (
    PresentationGenerationInput,
    PresentationMaterialResponse,
)
from app.modules.p2_gestion_documentos_preparacion.services.presentation_material_service import (
    PresentationMaterialService,
)

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]
Embeddings = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
Vectors = Annotated[VectorStoreProvider, Depends(get_vector_store_provider)]
GenerationRouter = Annotated[
    PresentationGenerationRouter, Depends(get_presentation_generation_router)
]


def _generate(
    document_id, body, current_user, db, embeddings, vectors, generation_router, regenerate
):
    material = PresentationMaterialService(
        db=db,
        embeddings=embeddings,
        vectors=vectors,
        generation_router=generation_router,
    ).generate(
        current_user,
        document_id,
        duration_minutes=body.duration_minutes,
        regenerate=regenerate,
    )
    return PresentationMaterialResponse.model_validate(material)


@router.post("/{document_id}/presentation/generate", response_model=PresentationMaterialResponse)
def generate_presentation(
    document_id: str,
    body: PresentationGenerationInput,
    current_user: CurrentUser,
    db: Database,
    embeddings: Embeddings,
    vectors: Vectors,
    generation_router: GenerationRouter,
) -> PresentationMaterialResponse:
    return _generate(
        document_id, body, current_user, db, embeddings, vectors, generation_router, False
    )


@router.post("/{document_id}/presentation/regenerate", response_model=PresentationMaterialResponse)
def regenerate_presentation(
    document_id: str,
    body: PresentationGenerationInput,
    current_user: CurrentUser,
    db: Database,
    embeddings: Embeddings,
    vectors: Vectors,
    generation_router: GenerationRouter,
) -> PresentationMaterialResponse:
    return _generate(
        document_id, body, current_user, db, embeddings, vectors, generation_router, True
    )


@router.get("/{document_id}/presentation", response_model=PresentationMaterialResponse)
def get_presentation(
    document_id: str,
    current_user: CurrentUser,
    db: Database,
) -> PresentationMaterialResponse:
    material = PresentationMaterialService(db=db).get(current_user, document_id)
    return PresentationMaterialResponse.model_validate(material)
