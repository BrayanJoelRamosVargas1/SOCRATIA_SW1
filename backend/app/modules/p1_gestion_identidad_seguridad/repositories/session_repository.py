from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.p1_gestion_identidad_seguridad.models.session import RefreshSession


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_session(
        self,
        *,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> RefreshSession:
        session = RefreshSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(session)
        self.db.flush()
        return session

    def get_by_token_hash(self, token_hash: str) -> RefreshSession | None:
        return self.db.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_hash))

    def revoke(self, session: RefreshSession, revoked_at: datetime) -> None:
        session.revoked_at = revoked_at
        self.db.flush()
