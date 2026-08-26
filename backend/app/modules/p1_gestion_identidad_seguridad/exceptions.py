from app.core.exceptions import DomainError


class InvalidCredentialsError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "Correo o contraseña incorrectos.",
            code="invalid_credentials",
            status_code=401,
        )


class InvalidSessionError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "La sesión expiró o fue revocada.",
            code="invalid_session",
            status_code=401,
        )


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
