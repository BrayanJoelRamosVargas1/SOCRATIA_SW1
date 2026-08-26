from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.users.dependencies import CurrentUser
from app.modules.users.schemas import UserResponse, UserUpdate
from app.modules.users.service import UserService

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.from_user(current_user)


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UserUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    user = UserService(db).update_profile(current_user, payload)
    return UserResponse.from_user(user)

