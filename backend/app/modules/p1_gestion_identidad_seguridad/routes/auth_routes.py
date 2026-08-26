from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.modules.p1_gestion_identidad_seguridad.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
)
from app.modules.p1_gestion_identidad_seguridad.schemas.user import UserResponse
from app.modules.p1_gestion_identidad_seguridad.services.auth_service import (
    AuthService,
    ClientContext,
    IssuedSession,
)

router = APIRouter()


def client_context(request: Request) -> ClientContext:
    forwarded = request.headers.get("x-forwarded-for")
    ip_address = forwarded.split(",")[0].strip() if forwarded else None
    if ip_address is None and request.client:
        ip_address = request.client.host
    return ClientContext(
        user_agent=request.headers.get("user-agent"),
        ip_address=ip_address,
    )


def set_auth_cookies(response: Response, issued: IssuedSession, settings: Settings) -> None:
    cookie_options = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "path": "/",
    }
    response.set_cookie(
        settings.access_cookie_name,
        issued.access_token,
        max_age=settings.access_token_expire_minutes * 60,
        **cookie_options,
    )
    response.set_cookie(
        settings.refresh_cookie_name,
        issued.refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        **cookie_options,
    )


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(settings.access_cookie_name, path="/")
    response.delete_cookie(settings.refresh_cookie_name, path="/")


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    settings = get_settings()
    issued = AuthService(db).register(payload, client_context(request))
    set_auth_cookies(response, issued, settings)
    return AuthResponse(user=UserResponse.from_user(issued.user))


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> AuthResponse:
    settings = get_settings()
    issued = AuthService(db).login(payload, client_context(request))
    set_auth_cookies(response, issued, settings)
    return AuthResponse(user=UserResponse.from_user(issued.user))


@router.post("/refresh", response_model=AuthResponse)
def refresh(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    refresh_cookie: Annotated[str | None, Cookie(alias="socratia_refresh")] = None,
) -> AuthResponse:
    settings = get_settings()
    token = request.cookies.get(settings.refresh_cookie_name) or refresh_cookie
    issued = AuthService(db).refresh(token, client_context(request))
    set_auth_cookies(response, issued, settings)
    return AuthResponse(user=UserResponse.from_user(issued.user))


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    refresh_cookie: Annotated[str | None, Cookie(alias="socratia_refresh")] = None,
) -> MessageResponse:
    settings = get_settings()
    token = request.cookies.get(settings.refresh_cookie_name) or refresh_cookie
    AuthService(db).logout(token)
    clear_auth_cookies(response, settings)
    return MessageResponse(message="Sesión cerrada.")
