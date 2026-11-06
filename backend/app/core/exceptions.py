from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class DomainError(Exception):
    def __init__(self, message: str, *, code: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        def field_message(item):
            kind=item["type"]
            if kind=="missing":return "Este campo es obligatorio."
            if kind=="string_too_short":return f"Escribe al menos {item['ctx']['min_length']} caracteres."
            if kind=="string_too_long":return f"Escribe como máximo {item['ctx']['max_length']} caracteres."
            if kind in {"int_parsing","int_type","float_parsing","float_type"}:return "Ingresa un número válido."
            if kind in {"literal_error","enum"}:return "Selecciona una opción válida."
            return "Revisa el formato y el valor de este campo."
        fields = [
            {"field": ".".join(str(part) for part in item["loc"][1:]), "message": field_message(item)}
            for item in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Revisa los datos enviados.",
                    "fields": fields,
                }
            },
        )
