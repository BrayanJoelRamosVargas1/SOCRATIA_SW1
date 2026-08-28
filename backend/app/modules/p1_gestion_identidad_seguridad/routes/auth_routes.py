from ipaddress import ip_address as parse_ip_address
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.integrations.email.base import EmailProvider
from app.integrations.email.dependencies import get_email_provider
from app.modules.p1_gestion_identidad_seguridad.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.modules.p1_gestion_identidad_seguridad.schemas.user import UserResponse
from app.modules.p1_gestion_identidad_seguridad.services.auth_service import (
    AuthService,
    ClientContext,
    IssuedSession,
)
from app.modules.p1_gestion_identidad_seguridad.services.password_reset_service import (
    GENERIC_RESPONSE,
    PasswordResetService,
    deliver_password_reset_email,
)

router = APIRouter()


def client_context(request: Request) -> ClientContext:
    settings = get_settings()
    raw_ip = request.client.host if request.client else None
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            raw_ip = forwarded.split(",", 1)[0].strip()
    try:
        ip_address = str(parse_ip_address(raw_ip)) if raw_ip else None
    except ValueError:
        ip_address = None
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


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    email_provider: Annotated[EmailProvider, Depends(get_email_provider)],
) -> MessageResponse:
    message = PasswordResetService(db).request_reset(str(payload.email), client_context(request))
    if message is not None:
        background_tasks.add_task(deliver_password_reset_email, email_provider, message)
    return MessageResponse(message=GENERIC_RESPONSE)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    settings = get_settings()
    PasswordResetService(db).reset_password(
        payload.token,
        payload.password,
        client_context(request),
    )
    clear_auth_cookies(response, settings)
    return MessageResponse(message="Tu contraseña fue restablecida. Ya puedes iniciar sesión.")


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
