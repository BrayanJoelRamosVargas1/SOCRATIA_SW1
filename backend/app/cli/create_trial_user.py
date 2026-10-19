"""Create a new private-trial account interactively; never overwrite existing accounts."""
import argparse
from getpass import getpass

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.p1_gestion_identidad_seguridad.repositories.user_repository import UserRepository
from app.modules.p1_gestion_identidad_seguridad.schemas.auth import RegisterRequest
from app.modules.p1_gestion_identidad_seguridad.policies.password import validate_new_password


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", choices=["admin", "student"], default="student")
    args = parser.parse_args()
    password = getpass("Nueva contraseña (no se mostrará): ")
    if password != getpass("Repite la contraseña: "):
        parser.error("Las contraseñas no coinciden.")
    payload = RegisterRequest(email=args.email, full_name=args.name, password=password)
    validate_new_password(password, email=str(payload.email), full_name=payload.full_name)
    with SessionLocal() as db:
        users = UserRepository(db)
        if users.get_by_email(str(payload.email)) is not None:
            parser.error("La cuenta ya existe. No se cambió su contraseña ni sus roles.")
        user = users.create(email=str(payload.email), full_name=payload.full_name, password_hash=hash_password(password))
        role_name = "Administrator" if args.role == "admin" else "student"
        user.roles.append(users.get_or_create_role(role_name))
        db.commit()
    print("Cuenta creada. La contraseña no se imprime ni se incluye en argumentos.")


if __name__ == "__main__":
    main()
