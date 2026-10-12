from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import AdminUser
from app.modules.p6_gestion_administracion.schemas.ai_settings import (
    AIOptionsResponse,
    AISettingsResponse,
    AISettingsUpdate,
)
from app.modules.p6_gestion_administracion.services.ai_configuration_service import (
    AIConfigurationService,
)

router = APIRouter()


@router.get(
    "/ai-settings",
    response_model=AISettingsResponse,
    summary="Get active AI configuration",
)
def get_ai_settings(
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> AISettingsResponse:
    service = AIConfigurationService(db)
    settings = service.get_or_create_settings()
    return AISettingsResponse.model_validate(settings)


@router.patch(
    "/ai-settings",
    response_model=AISettingsResponse,
    summary="Update AI configuration at runtime",
)
def patch_ai_settings(
    payload: AISettingsUpdate,
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> AISettingsResponse:
    service = AIConfigurationService(db)
    updated = service.update_settings(admin_id=admin.id, payload=payload)
    return AISettingsResponse.model_validate(updated)


@router.get(
    "/ai-settings/options",
    response_model=AIOptionsResponse,
    summary="Get available AI providers, models, and limits",
)
def get_ai_options(
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
) -> AIOptionsResponse:
    service = AIConfigurationService(db)
    return service.get_options()
