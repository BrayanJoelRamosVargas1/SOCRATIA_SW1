from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.p1_gestion_identidad_seguridad.models.password_reset import PasswordResetToken


class PasswordResetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, user_id: str, token_hash: str, expires_at: datetime) -> PasswordResetToken:
        token = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(token)
        self.db.flush()
        return token

    def get_by_hash_for_update(self, token_hash: str) -> PasswordResetToken | None:
        statement = (
            select(PasswordResetToken)
            .where(PasswordResetToken.token_hash == token_hash)
            .with_for_update()
        )
        return self.db.scalar(statement)

    def invalidate_active_for_user(self, user_id: str, used_at: datetime) -> None:
        statement = (
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=used_at)
        )
        self.db.execute(statement)
        self.db.flush()
