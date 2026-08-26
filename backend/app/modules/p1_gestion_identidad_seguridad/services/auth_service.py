from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.modules.p1_gestion_identidad_seguridad.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidSessionError,
)
from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p1_gestion_identidad_seguridad.repositories.session_repository import (
    SessionRepository,
)
from app.modules.p1_gestion_identidad_seguridad.repositories.user_repository import (
    UserRepository,
)
from app.modules.p1_gestion_identidad_seguridad.schemas.auth import LoginRequest, RegisterRequest


@dataclass(frozen=True)
class ClientContext:
    user_agent: str | None
    ip_address: str | None


@dataclass(frozen=True)
class IssuedSession:
    user: User
    access_token: str
    refresh_token: str


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.sessions = SessionRepository(db)
        self.settings = get_settings()

    def register(self, payload: RegisterRequest, context: ClientContext) -> IssuedSession:
        email = str(payload.email).lower()
        if self.users.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError

        user = self.users.create(
            email=email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
        )
        student_role = self.users.get_or_create_role(
            "student", "Estudiante que prepara y practica defensas académicas."
        )
        user.roles.append(student_role)

        try:
            issued = self._issue(user, context)
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise EmailAlreadyRegisteredError from exc
        self.db.refresh(user)
        return issued

    def login(self, payload: LoginRequest, context: ClientContext) -> IssuedSession:
        user = self.users.get_by_email(str(payload.email))
        if user is None:
            verify_password(payload.password, DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError
        if not verify_password(payload.password, user.password_hash) or not user.is_active:
            raise InvalidCredentialsError

        issued = self._issue(user, context)
        self.db.commit()
        return issued

    def refresh(self, refresh_token: str | None, context: ClientContext) -> IssuedSession:
        if not refresh_token:
            raise InvalidSessionError

        current = self.sessions.get_by_token_hash(hash_refresh_token(refresh_token))
        now = datetime.now(UTC)
        if (
            current is None
            or current.revoked_at is not None
            or self._as_utc(current.expires_at) <= now
            or not current.user.is_active
        ):
            raise InvalidSessionError

        self.sessions.revoke(current, now)
        issued = self._issue(current.user, context)
        self.db.commit()
        return issued

    def logout(self, refresh_token: str | None) -> None:
        if refresh_token:
            current = self.sessions.get_by_token_hash(hash_refresh_token(refresh_token))
            if current is not None and current.revoked_at is None:
                self.sessions.revoke(current, datetime.now(UTC))
                self.db.commit()

    def _issue(self, user: User, context: ClientContext) -> IssuedSession:
        refresh_token = create_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.refresh_token_expire_days)
        self.sessions.create_session(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=expires_at,
            user_agent=context.user_agent,
            ip_address=context.ip_address,
        )
        return IssuedSession(
            user=user,
            access_token=create_access_token(user.id),
            refresh_token=refresh_token,
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
