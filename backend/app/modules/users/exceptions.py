from app.core.exceptions import DomainError


class UserNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__("Usuario no encontrado.", code="user_not_found", status_code=404)


class EmailAlreadyRegisteredError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "Ya existe una cuenta con este correo.",
            code="email_already_registered",
            status_code=409,
        )

