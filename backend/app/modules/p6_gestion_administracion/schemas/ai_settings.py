from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

VALID_PROVIDERS = {"groq", "gemini"}

VALID_MODELS_BY_PROVIDER = {
    "groq": {
        "openai/gpt-oss-20b",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
    },
    "gemini": {
        "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-2.5-flash",
    },
}


class AISettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    jury_provider: str
    jury_model: str
    jury_temperature: float
    jury_max_tokens: int
    max_followups: int
    retrieval_top_k: int
    evaluation_provider: str
    evaluation_model: str
    evaluation_temperature: float
    fallback_enabled: bool
    config_version: int
    updated_at: datetime | None = None
    updated_by: str | None = None


class AISettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jury_provider: str | None = None
    jury_model: Annotated[str, Field(min_length=1)] | None = None
    jury_temperature: Annotated[float, Field(ge=0.0, le=1.0)] | None = None
    jury_max_tokens: Annotated[int, Field(ge=256, le=4096)] | None = None
    max_followups: Annotated[int, Field(ge=0, le=5)] | None = None
    retrieval_top_k: Annotated[int, Field(ge=1, le=20)] | None = None
    evaluation_provider: str | None = None
    evaluation_model: Annotated[str, Field(min_length=1)] | None = None
    evaluation_temperature: Annotated[float, Field(ge=0.0, le=1.0)] | None = None
    fallback_enabled: bool | None = None

    @field_validator("jury_provider", mode="after")
    @classmethod
    def validate_jury_provider(cls, value: str | None) -> str | None:
        if value is not None and value.lower() not in VALID_PROVIDERS:
            raise ValueError(f"Proveedor no soportado: '{value}'. Permitidos: {sorted(VALID_PROVIDERS)}")
        return value.lower() if value is not None else None

    @field_validator("evaluation_provider", mode="after")
    @classmethod
    def validate_evaluation_provider(cls, value: str | None) -> str | None:
        if value is not None and value.lower() not in VALID_PROVIDERS:
            raise ValueError(f"Proveedor no soportado: '{value}'. Permitidos: {sorted(VALID_PROVIDERS)}")
        return value.lower() if value is not None else None

    @model_validator(mode="after")
    def validate_model_provider_compatibility(self) -> "AISettingsUpdate":
        if self.jury_provider and self.jury_model:
            allowed = VALID_MODELS_BY_PROVIDER.get(self.jury_provider, set())
            if self.jury_model not in allowed:
                raise ValueError(
                    f"Modelo '{self.jury_model}' no compatible con proveedor '{self.jury_provider}'. "
                    f"Modelos válidos: {sorted(allowed)}"
                )
        if self.evaluation_provider and self.evaluation_model:
            allowed = VALID_MODELS_BY_PROVIDER.get(self.evaluation_provider, set())
            if self.evaluation_model not in allowed:
                raise ValueError(
                    f"Modelo '{self.evaluation_model}' no compatible con proveedor '{self.evaluation_provider}'. "
                    f"Modelos válidos: {sorted(allowed)}"
                )
        return self


class AIProviderOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    models: list[str]
    is_configured: bool


class AIRangeLimit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min: float
    max: float
    step: float | None = None


class AIOptionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    providers: list[AIProviderOption]
    limits: dict[str, AIRangeLimit]
