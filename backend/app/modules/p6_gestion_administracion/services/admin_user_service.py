import math

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.p1_gestion_identidad_seguridad.models.user import Role, User
from app.modules.p1_gestion_identidad_seguridad.repositories.user_repository import UserRepository
from app.modules.p6_gestion_administracion.schemas.admin_users import AdminUserUpdate


class AdminUserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repo = UserRepository(db)

    def list_users(self, page: int, size: int, search: str | None = None, role: str | None = None, is_active: bool | None = None):
        query = select(User)

        if search:
            query = query.where(
                or_(
                    User.full_name.ilike(f"%{search}%"),
                    User.email.ilike(f"%{search}%")
                )
            )

        if is_active is not None:
            query = query.where(User.is_active == is_active)
            
        if role:
            query = query.join(User.roles).where(Role.name == role)

        total = self.db.scalar(select(func.count()).select_from(query.subquery()))
        
        query = query.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size)
        items = self.db.scalars(query).all()
        
        pages = math.ceil(total / size) if total else 0
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }

    def get_user(self, user_id: str) -> User:
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user

    def update_user(self, current_admin: User, target_user_id: str, payload: AdminUserUpdate) -> User:
        user = self.get_user(target_user_id)
        
        changes = payload.model_dump(exclude_unset=True)
        
        # Protect last admin logic
        is_admin_currently = any(r.name == "Administrator" for r in user.roles)
        if is_admin_currently:
            # If changing roles to not include Administrator, or deactivating
            removing_admin = False
            if "roles" in changes and "Administrator" not in changes["roles"]:
                removing_admin = True
            if "is_active" in changes and not changes["is_active"]:
                removing_admin = True
                
            if removing_admin:
                # check if there are other active admins
                active_admins_query = select(func.count(User.id)).join(User.roles).where(Role.name == "Administrator", User.is_active, User.id != user.id)
                other_admins_count = self.db.scalar(active_admins_query)
                if other_admins_count == 0:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable or change role of the last active administrator")
        
        if "full_name" in changes and changes["full_name"] is not None:
            user.full_name = changes["full_name"].strip()
            
        if "email" in changes and changes["email"] is not None:
            email = str(changes["email"]).lower()
            existing = self.user_repo.get_by_email(email)
            if existing and existing.id != user.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
            user.email = email
            
        if "is_active" in changes and changes["is_active"] is not None:
            # When deactivated, auth_version is bumped to invalidate sessions? 
            # Well, get_current_user already checks user.is_active. 
            # But bumping auth_version ensures that ANY issued tokens are completely dead even if cached.
            if user.is_active and not changes["is_active"]:
                user.auth_version += 1
            user.is_active = changes["is_active"]
            
        if "roles" in changes and changes["roles"] is not None:
            new_roles = []
            for r_name in changes["roles"]:
                role = self.user_repo.get_or_create_role(r_name)
                new_roles.append(role)
            # auth_version bump if roles change to revoke access? Yes, good practice.
            user.auth_version += 1
            user.roles = new_roles
            
        self.db.commit()
        self.db.refresh(user)
        return user
