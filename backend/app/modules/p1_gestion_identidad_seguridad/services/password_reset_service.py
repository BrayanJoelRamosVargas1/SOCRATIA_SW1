import html
import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import (
    create_password_reset_token,
    hash_password,
    hash_password_reset_token,
)
from app.integrations.email.base import EmailDeliveryError, EmailProvider, OutboundEmail
from app.modules.p1_gestion_identidad_seguridad.exceptions import (
    InvalidPasswordResetTokenError,
)
from app.modules.p1_gestion_identidad_seguridad.policies.password import validate_new_password
from app.modules.p1_gestion_identidad_seguridad.repositories.password_reset_repository import (
    PasswordResetRepository,
)
from app.modules.p1_gestion_identidad_seguridad.repositories.session_repository import (
    SessionRepository,
)
from app.modules.p1_gestion_identidad_seguridad.repositories.user_repository import (
    UserRepository,
)
from app.modules.p1_gestion_identidad_seguridad.services.auth_service import ClientContext
from app.modules.p1_gestion_identidad_seguridad.services.login_security_service import (
    LoginSecurityService,
)

logger = logging.getLogger(__name__)
GENERIC_RESPONSE = (
    "Si existe una cuenta con ese correo, recibirás un enlace para restablecer tu contraseña."
)


class PasswordResetService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.users = UserRepository(db)
        self.tokens = PasswordResetRepository(db)
        self.sessions = SessionRepository(db)
        self.login_security = LoginSecurityService(db, self.settings)

    def request_reset(self, email: str, context: ClientContext) -> OutboundEmail | None:
        normalized_email = email.lower()
        now = datetime.now(UTC)
        identifier_hash = self.login_security.hash_identifier(normalized_email)
        user = self.users.get_by_email(normalized_email, for_update=True)
        limited = self.login_security.password_reset_is_rate_limited(
            identifier_hash,
            context.ip_address,
            now,
        )
        self.login_security.record_password_reset_request(
            user_id=user.id if user else None,
            identifier_hash=identifier_hash,
            ip_address=context.ip_address,
            now=now,
        )

        if limited or user is None or not user.is_active:
            # Preserve comparable cryptographic work without revealing whether the account exists.
            hash_password_reset_token(create_password_reset_token())
            self.db.commit()
            return None

        self.tokens.invalidate_active_for_user(user.id, now)
        raw_token = create_password_reset_token()
        self.tokens.create(
            user_id=user.id,
            token_hash=hash_password_reset_token(raw_token),
            expires_at=now + timedelta(minutes=self.settings.password_reset_token_ttl_minutes),
        )
        self.db.commit()
        return self._build_email(user.email, user.full_name, raw_token)

    def reset_password(self, raw_token: str, password: str, context: ClientContext) -> None:
        now = datetime.now(UTC)
        token = self.tokens.get_by_hash_for_update(hash_password_reset_token(raw_token))
        if (
            token is None
            or token.used_at is not None
            or self._as_utc(token.expires_at) <= now
        ):
            raise InvalidPasswordResetTokenError

        user = self.users.get_by_id(token.user_id)
        if user is None or not user.is_active:
            raise InvalidPasswordResetTokenError

        validate_new_password(password, email=user.email, full_name=user.full_name)
        self.users.update_password_hash(user, hash_password(password))
        self.tokens.invalidate_active_for_user(user.id, now)
        self.sessions.revoke_all_for_user(user.id, now)
        self.login_security.reset_for_user(user.id, now)
        self.login_security.record_password_reset_completed(
            user_id=user.id,
            ip_address=context.ip_address,
            now=now,
        )
        self.db.commit()

    def _build_email(self, recipient: str, full_name: str, raw_token: str) -> OutboundEmail:
        reset_url = (
            f"{self.settings.frontend_url.rstrip('/')}/reset-password?"
            f"{urlencode({'token': raw_token})}"
        )
        safe_name = html.escape(full_name)
        safe_url = html.escape(reset_url, quote=True)
        minutes = self.settings.password_reset_token_ttl_minutes
        return OutboundEmail(
            recipient=recipient,
            subject="Restablece tu contraseña de Socratia",
            text_body=(
                f"Hola, {full_name}.\n\n"
                "Recibimos una solicitud para restablecer tu contraseña de Socratia. "
                f"Abre este enlace dentro de los próximos {minutes} minutos:\n\n"
                f"{reset_url}\n\n"
                "Si no solicitaste este cambio, ignora este correo."
            ),
            html_body=(
                "<!doctype html><html><body>"
                f"<p>Hola, {safe_name}.</p>"
                "<p>Recibimos una solicitud para restablecer tu contraseña de Socratia.</p>"
                f'<p><a href="{safe_url}">Restablecer mi contraseña</a></p>'
                f"<p>Este enlace vence en {minutes} minutos y solo puede usarse una vez.</p>"
                "<p>Si no solicitaste este cambio, ignora este correo.</p>"
                "</body></html>"
            ),
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def deliver_password_reset_email(provider: EmailProvider, message: OutboundEmail) -> None:
    try:
        provider.send(message)
        logger.info("Password reset email accepted by SMTP relay")
    except EmailDeliveryError:
        # The public response stays generic. No address or token is written to logs.
        logger.exception("Password reset email delivery failed")
