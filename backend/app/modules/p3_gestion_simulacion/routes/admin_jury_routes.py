from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import AdminUser
from app.modules.p3_gestion_simulacion.schemas.simulation import (
    AdminJuryProfileResponse,
    JuryProfileCreateInput,
    JuryProfileUpdateInput,
)
from app.modules.p3_gestion_simulacion.services.admin_jury_service import (
    AdminJuryProfileService,
)

router = APIRouter()
Database = Annotated[Session, Depends(get_db)]


@router.get("/jury-profiles", response_model=list[AdminJuryProfileResponse])
def list_admin_jury_profiles(
    admin_user: AdminUser,
    db: Database,
) -> list[AdminJuryProfileResponse]:
    del admin_user
    profiles = AdminJuryProfileService(db).list_all()
    return [AdminJuryProfileResponse.model_validate(p) for p in profiles]


@router.post(
    "/jury-profiles", response_model=AdminJuryProfileResponse, status_code=status.HTTP_201_CREATED
)
def create_jury_profile(
    body: JuryProfileCreateInput,
    admin_user: AdminUser,
    db: Database,
) -> AdminJuryProfileResponse:
    del admin_user
    profile = AdminJuryProfileService(db).create(body)
    return AdminJuryProfileResponse.model_validate(profile)


@router.get("/jury-profiles/{profile_id}", response_model=AdminJuryProfileResponse)
def get_jury_profile(
    profile_id: str,
    admin_user: AdminUser,
    db: Database,
) -> AdminJuryProfileResponse:
    del admin_user
    profile = AdminJuryProfileService(db).get(profile_id)
    return AdminJuryProfileResponse.model_validate(profile)


@router.patch("/jury-profiles/{profile_id}", response_model=AdminJuryProfileResponse)
def update_jury_profile(
    profile_id: str,
    body: JuryProfileUpdateInput,
    admin_user: AdminUser,
    db: Database,
) -> AdminJuryProfileResponse:
    del admin_user
    profile = AdminJuryProfileService(db).update(profile_id, body)
    return AdminJuryProfileResponse.model_validate(profile)


@router.put("/jury-profiles/{profile_id}", response_model=AdminJuryProfileResponse)
def update_jury_profile_put(
    profile_id: str,
    body: JuryProfileUpdateInput,
    admin_user: AdminUser,
    db: Database,
) -> AdminJuryProfileResponse:
    del admin_user
    profile = AdminJuryProfileService(db).update(profile_id, body)
    return AdminJuryProfileResponse.model_validate(profile)


@router.delete("/jury-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_jury_profile(
    profile_id: str,
    admin_user: AdminUser,
    db: Database,
) -> Response:
    del admin_user
    AdminJuryProfileService(db).delete(profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
