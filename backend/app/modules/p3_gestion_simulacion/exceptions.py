from app.core.exceptions import DomainError


class SimulationNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__("Simulación no encontrada.", code="simulation_not_found", status_code=404)


class JuryProfileNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "Perfil de jurado no disponible.",
            code="jury_profile_not_found",
            status_code=404,
        )


class SimulationDocumentNotReadyError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "El documento debe estar procesado y tener un banco de preguntas listo.",
            code="simulation_document_not_ready",
            status_code=409,
        )


class InvalidSimulationTransitionError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "La transición solicitada no es válida para esta simulación.",
            code="invalid_simulation_transition",
            status_code=409,
        )


class SimulationCannotBeDeletedError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "Sólo puedes eliminar simulaciones en preparación.",
            code="simulation_cannot_be_deleted",
            status_code=409,
        )


class SimulationNotReadyError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "La simulación debe estar lista y conservar sus 12 preguntas.",
            code="simulation_not_ready",
            status_code=409,
        )


class SimulationNotActiveError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "La sesión de simulación no está activa.",
            code="simulation_not_active",
            status_code=409,
        )


class InvalidTurnError(DomainError):
    def __init__(self, message: str = "La respuesta no corresponde al turno actual.") -> None:
        super().__init__(message, code="invalid_turn", status_code=409)
