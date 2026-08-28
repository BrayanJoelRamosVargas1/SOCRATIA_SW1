import hashlib
import hmac
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.modules.p1_gestion_identidad_seguridad.models.login_security import (
    AuthenticationEventType,
    LoginSecurity,
)
from app.modules.p1_gestion_identidad_seguridad.repositories.login_security_repository import (
    LoginSecurityRepository,
)

OBSERVATION_WINDOW = timedelta(hours=24)
LOCK_DURATIONS = {
    1: timedelta(minutes=5),
    2: timedelta(minutes=10),
    3: timedelta(minutes=15),
}
LOGIN_REQUEST_EVENTS = (
    AuthenticationEventType.LOGIN_FAILED.value,
    AuthenticationEventType.LOGIN_REJECTED_LOCKED.value,
    AuthenticationEventType.LOGIN_RATE_LIMITED.value,
    AuthenticationEventType.LOGIN_SUCCESS.value,
)


class LoginSecurityService:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.repository = LoginSecurityRepository(db)
        self.settings = settings or get_settings()

    def ip_is_rate_limited(self, ip_address: str | None, now: datetime) -> bool:
        if not ip_address:
            return False
        since = now - timedelta(seconds=self.settings.login_ip_window_seconds)
        attempts = self.repository.count_ip_login_attempts(
            ip_address,
            since=since,
            request_event_types=LOGIN_REQUEST_EVENTS,
        )
        return attempts >= self.settings.login_ip_max_attempts

    def prepare_state(self, user_id: str, now: datetime) -> LoginSecurity:
        state = self.repository.get_for_user(user_id, for_update=True)
        if state is None:
            state = self.repository.create_for_user(user_id)
        if state.last_failed_at and self._as_utc(state.last_failed_at) <= now - OBSERVATION_WINDOW:
            self._reset_state(state)
        return state

    @staticmethod
    def is_locked(state: LoginSecurity, now: datetime) -> bool:
        return state.locked_until is not None and LoginSecurityService._as_utc(
            state.locked_until
        ) > now

    def record_failure(
        self,
        state: LoginSecurity,
        *,
        now: datetime,
        ip_address: str | None,
    ) -> None:
        state.failed_attempts += 1
        state.last_failed_at = now
        state.updated_at = now
        self.repository.record_event(
            event_type=AuthenticationEventType.LOGIN_FAILED.value,
            user_id=state.user_id,
            ip_address=ip_address,
            created_at=now,
        )
        if state.failed_attempts >= 3:
            state.lock_level = min(state.failed_attempts - 2, 3)
            state.locked_until = now + LOCK_DURATIONS[state.lock_level]
            self.repository.record_event(
                event_type=AuthenticationEventType.LOGIN_LOCKED.value,
                user_id=state.user_id,
                ip_address=ip_address,
                created_at=now,
            )

    def record_locked_attempt(
        self,
        state: LoginSecurity,
        *,
        now: datetime,
        ip_address: str | None,
    ) -> None:
        self.repository.record_event(
            event_type=AuthenticationEventType.LOGIN_REJECTED_LOCKED.value,
            user_id=state.user_id,
            ip_address=ip_address,
            created_at=now,
        )

    def record_unknown_failure(
        self,
        email: str,
        *,
        now: datetime,
        ip_address: str | None,
    ) -> None:
        self.repository.record_event(
            event_type=AuthenticationEventType.LOGIN_FAILED.value,
            identifier_hash=self.hash_identifier(email),
            ip_address=ip_address,
            created_at=now,
        )

    def record_rate_limited(
        self,
        email: str,
        *,
        now: datetime,
        ip_address: str | None,
    ) -> None:
        self.repository.record_event(
            event_type=AuthenticationEventType.LOGIN_RATE_LIMITED.value,
            identifier_hash=self.hash_identifier(email),
            ip_address=ip_address,
            created_at=now,
        )

    def record_success(
        self,
        user_id: str,
        *,
        now: datetime,
        ip_address: str | None,
    ) -> None:
        state = self.repository.get_for_user(user_id, for_update=True)
        if state is not None:
            self._reset_state(state)
            state.updated_at = now
        self.repository.record_event(
            event_type=AuthenticationEventType.LOGIN_SUCCESS.value,
            user_id=user_id,
            ip_address=ip_address,
            created_at=now,
        )

    def reset_for_user(self, user_id: str, now: datetime) -> None:
        state = self.repository.get_for_user(user_id, for_update=True)
        if state is not None:
            self._reset_state(state)
            state.updated_at = now

    def password_reset_is_rate_limited(
        self,
        identifier_hash: str,
        ip_address: str | None,
        now: datetime,
    ) -> bool:
        since = now - timedelta(seconds=self.settings.password_reset_rate_window_seconds)
        identifier_count = self.repository.count_password_reset_requests(
            since=since,
            identifier_hash=identifier_hash,
        )
        ip_count = (
            self.repository.count_password_reset_requests(since=since, ip_address=ip_address)
            if ip_address
            else 0
        )
        return (
            identifier_count >= self.settings.password_reset_max_requests_per_identifier
            or ip_count >= self.settings.password_reset_max_requests_per_ip
        )

    def record_password_reset_request(
        self,
        *,
        user_id: str | None,
        identifier_hash: str,
        ip_address: str | None,
        now: datetime,
    ) -> None:
        self.repository.record_event(
            event_type=AuthenticationEventType.PASSWORD_RESET_REQUESTED.value,
            user_id=user_id,
            identifier_hash=identifier_hash,
            ip_address=ip_address,
            created_at=now,
        )

    def record_password_reset_completed(
        self,
        *,
        user_id: str,
        ip_address: str | None,
        now: datetime,
    ) -> None:
        self.repository.record_event(
            event_type=AuthenticationEventType.PASSWORD_RESET_COMPLETED.value,
            user_id=user_id,
            ip_address=ip_address,
            created_at=now,
        )

    def hash_identifier(self, value: str) -> str:
        return hmac.new(
            self.settings.jwt_secret.encode("utf-8"),
            value.casefold().encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _reset_state(state: LoginSecurity) -> None:
        state.failed_attempts = 0
        state.lock_level = 0
        state.locked_until = None
        state.last_failed_at = None

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
