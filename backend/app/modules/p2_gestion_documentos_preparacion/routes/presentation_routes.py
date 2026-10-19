from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.integrations.llm.dependencies import get_presentation_generation_router
from app.integrations.llm.presentation_router import PresentationGenerationRouter
from app.integrations.retrieval.dependencies import get_retrieval_router
from app.integrations.retrieval.router import RetrievalRouter
from app.integrations.storage.base import StorageProvider
from app.integrations.storage.dependencies import get_storage_provider
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import CurrentUser
from app.modules.p2_gestion_documentos_preparacion.schemas.presentation_material import (
    PresentationGenerationInput,
    PresentationMaterialResponse,
)
from app.modules.p2_gestion_documentos_preparacion.services.document_service import DocumentService
from app.modules.p2_gestion_documentos_preparacion.services.presentation_export import (
    export_presentation,
)
from app.modules.p2_gestion_documentos_preparacion.services.presentation_material_service import (
    PresentationMaterialService,
)

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]


@router.get("/{document_id}/presentation/export")
def download_presentation(document_id: str, current_user: CurrentUser, db: Database,
                          storage: Annotated[StorageProvider, Depends(get_storage_provider)]) -> Response:
    # Both services enforce ownership before any file contents are read.
    document = DocumentService(db, storage).get_for(current_user, document_id)
    material = PresentationMaterialService(db=db).get(current_user, document_id)
    pdf_content = storage.read(document.storage_key) if document.file_type == "PDF" else None
    content = export_presentation(material, source_name=document.original_name, pdf_content=pdf_content)
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    headers={"Content-Disposition": 'attachment; filename="socratia-defensa.pptx"',
                             "Cache-Control": "private, no-store"})
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
