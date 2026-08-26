from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.users.exceptions import EmailAlreadyRegisteredError
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserUpdate


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def update_profile(self, user: User, payload: UserUpdate) -> User:
        changes = payload.model_dump(exclude_unset=True)
        if "email" in changes and changes["email"] is not None:
            email = str(changes["email"]).lower()
            existing = self.users.get_by_email(email)
            if existing is not None and existing.id != user.id:
                raise EmailAlreadyRegisteredError
            user.email = email
        if "full_name" in changes and changes["full_name"] is not None:
            user.full_name = changes["full_name"].strip()

        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise EmailAlreadyRegisteredError from exc
        self.db.refresh(user)
        return user

