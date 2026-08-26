from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.users.models import Role, User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(func.lower(User.email) == email.lower())
        return self.db.scalar(statement)

    def create(self, *, email: str, full_name: str, password_hash: str) -> User:
        user = User(email=email.lower(), full_name=full_name.strip(), password_hash=password_hash)
        self.db.add(user)
        self.db.flush()
        return user

    def get_or_create_role(self, name: str, description: str | None = None) -> Role:
        role = self.db.scalar(select(Role).where(Role.name == name))
        if role is None:
            role = Role(name=name, description=description)
            self.db.add(role)
            self.db.flush()
        return role

