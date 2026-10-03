from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.integrations.llm.dependencies import get_presentation_generation_router
from app.integrations.llm.presentation_router import PresentationGenerationRouter
from app.integrations.retrieval.dependencies import get_retrieval_router
from app.integrations.retrieval.router import RetrievalRouter
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
Retrieval = Annotated[RetrievalRouter, Depends(get_retrieval_router)]
GenerationRouter = Annotated[
    PresentationGenerationRouter, Depends(get_presentation_generation_router)
]


def _generate(document_id, body, current_user, db, retrieval_router, generation_router, regenerate):
    material = PresentationMaterialService(
        db=db,
        retrieval_router=retrieval_router,
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
    retrieval_router: Retrieval,
    generation_router: GenerationRouter,
) -> PresentationMaterialResponse:
    return _generate(
        document_id, body, current_user, db, retrieval_router, generation_router, False
    )


@router.post("/{document_id}/presentation/regenerate", response_model=PresentationMaterialResponse)
def regenerate_presentation(
    document_id: str,
    body: PresentationGenerationInput,
    current_user: CurrentUser,
    db: Database,
    retrieval_router: Retrieval,
    generation_router: GenerationRouter,
) -> PresentationMaterialResponse:
    return _generate(document_id, body, current_user, db, retrieval_router, generation_router, True)


@router.get("/{document_id}/presentation", response_model=PresentationMaterialResponse)
def get_presentation(
    document_id: str,
    current_user: CurrentUser,
    db: Database,
) -> PresentationMaterialResponse:
    material = PresentationMaterialService(db=db).get(current_user, document_id)
    return PresentationMaterialResponse.model_validate(material)
