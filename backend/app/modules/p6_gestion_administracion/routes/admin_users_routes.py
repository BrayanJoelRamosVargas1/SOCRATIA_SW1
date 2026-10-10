from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.p1_gestion_identidad_seguridad.policies.current_user import AdminUser
from app.modules.p1_gestion_identidad_seguridad.schemas.user import UserResponse
from app.modules.p6_gestion_administracion.schemas.admin_users import AdminUserUpdate
from app.modules.p6_gestion_administracion.services.admin_user_service import AdminUserService

router = APIRouter()

@router.get("/users")
def list_users(
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    role: str | None = None,
    is_active: bool | None = None
) -> dict[str, Any]:
    service = AdminUserService(db)
    result = service.list_users(page, size, search, role, is_active)
    result["items"] = [UserResponse.from_user(u).model_dump() for u in result["items"]]
    return result

@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)]
) -> Any:
    service = AdminUserService(db)
    user = service.get_user(user_id)
    return UserResponse.from_user(user)

@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    payload: AdminUserUpdate,
    admin: AdminUser,
    db: Annotated[Session, Depends(get_db)]
) -> Any:
    service = AdminUserService(db)
    user = service.update_user(admin, user_id, payload)
    return UserResponse.from_user(user)
