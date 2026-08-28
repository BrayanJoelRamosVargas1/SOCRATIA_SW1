from app.core.exceptions import DomainError


class InvalidCredentialsError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "No se pudo iniciar sesión. Verifica tus datos o, si realizaste varios intentos, "
            "espera unos minutos.",
            code="invalid_credentials",
            status_code=401,
        )


class LoginRateLimitError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "Demasiados intentos de inicio de sesión. Espera unos minutos y vuelve a intentarlo.",
            code="login_rate_limited",
            status_code=429,
        )


class InvalidSessionError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "La sesión expiró o fue revocada.",
            code="invalid_session",
            status_code=401,
        )


class WeakPasswordError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="weak_password", status_code=422)


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


class InvalidPasswordResetTokenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "El enlace de recuperación no es válido, ya fue utilizado o expiró.",
            code="invalid_password_reset_token",
            status_code=400,
        )
