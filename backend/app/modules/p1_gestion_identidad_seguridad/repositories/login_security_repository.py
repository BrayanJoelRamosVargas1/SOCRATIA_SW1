from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.p1_gestion_identidad_seguridad.models.login_security import (
    AuthenticationEvent,
    LoginSecurity,
)


class LoginSecurityRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_user(self, user_id: str, *, for_update: bool = False) -> LoginSecurity | None:
        statement = select(LoginSecurity).where(LoginSecurity.user_id == user_id)
        if for_update:
            statement = statement.with_for_update()
        return self.db.scalar(statement)

    def create_for_user(self, user_id: str) -> LoginSecurity:
        state = LoginSecurity(user_id=user_id)
        self.db.add(state)
        self.db.flush()
        return state

    def record_event(
        self,
        *,
        event_type: str,
        created_at: datetime,
        user_id: str | None = None,
        ip_address: str | None = None,
        identifier_hash: str | None = None,
    ) -> AuthenticationEvent:
        event = AuthenticationEvent(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            identifier_hash=identifier_hash,
            created_at=created_at,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def count_ip_login_attempts(
        self,
        ip_address: str,
        *,
        since: datetime,
        request_event_types: tuple[str, ...],
    ) -> int:
        statement = select(func.count(AuthenticationEvent.id)).where(
            AuthenticationEvent.ip_address == ip_address,
            AuthenticationEvent.created_at >= since,
            AuthenticationEvent.event_type.in_(request_event_types),
        )
        return int(self.db.scalar(statement) or 0)

    def count_password_reset_requests(
        self,
        *,
        since: datetime,
        identifier_hash: str | None = None,
        ip_address: str | None = None,
    ) -> int:
        statement = select(func.count(AuthenticationEvent.id)).where(
            AuthenticationEvent.event_type == "PASSWORD_RESET_REQUESTED",
            AuthenticationEvent.created_at >= since,
        )
        if identifier_hash is not None:
            statement = statement.where(AuthenticationEvent.identifier_hash == identifier_hash)
        if ip_address is not None:
            statement = statement.where(AuthenticationEvent.ip_address == ip_address)
        return int(self.db.scalar(statement) or 0)
