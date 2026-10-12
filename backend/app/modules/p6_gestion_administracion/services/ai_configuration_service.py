import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.modules.p6_gestion_administracion.models.ai_settings import AISettings
from app.modules.p6_gestion_administracion.schemas.ai_settings import (
    VALID_MODELS_BY_PROVIDER,
    AIOptionsResponse,
    AIProviderOption,
    AIRangeLimit,
    AISettingsUpdate,
)

logger = logging.getLogger(__name__)

SINGLETON_SETTINGS_ID = "default"


class AIConfigurationService:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def get_or_create_settings(self) -> AISettings:
        if self.db is None:
            return self._build_default_in_memory()

        record = self.db.query(AISettings).filter_by(id=SINGLETON_SETTINGS_ID).first()
        if record is None:
            settings = get_settings()
            record = AISettings(
                id=SINGLETON_SETTINGS_ID,
                jury_provider="groq",
                jury_model=settings.groq_question_model or "openai/gpt-oss-20b",
                jury_temperature=0.2,
                jury_max_tokens=2048,
                max_followups=2,
                retrieval_top_k=settings.question_retrieval_top_k or 4,
                evaluation_provider="groq",
                evaluation_model=settings.groq_question_model or "openai/gpt-oss-20b",
                evaluation_temperature=0.0,
                fallback_enabled=True,
                config_version=1,
                updated_at=datetime.now(UTC),
                updated_by=None,
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            logger.info("Initialized default AISettings record in database.")
        return record

    def get_active_config(self) -> AISettings:
        return self.get_or_create_settings()

    def update_settings(self, admin_id: str, payload: AISettingsUpdate) -> AISettings:
        if self.db is None:
            raise RuntimeError("Database session required to update AI settings")

        record = self.get_or_create_settings()
        update_data = payload.model_dump(exclude_unset=True)

        target_jury_provider = update_data.get("jury_provider", record.jury_provider)
        target_jury_model = update_data.get("jury_model", record.jury_model)
        if target_jury_model not in VALID_MODELS_BY_PROVIDER.get(target_jury_provider, set()):
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Modelo '{target_jury_model}' no compatible con proveedor '{target_jury_provider}'",
            )

        target_eval_provider = update_data.get("evaluation_provider", record.evaluation_provider)
        target_eval_model = update_data.get("evaluation_model", record.evaluation_model)
        if target_eval_model not in VALID_MODELS_BY_PROVIDER.get(target_eval_provider, set()):
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Modelo '{target_eval_model}' no compatible con proveedor '{target_eval_provider}'",
            )

        for key, value in update_data.items():
            setattr(record, key, value)

        record.config_version += 1
        record.updated_at = datetime.now(UTC)
        record.updated_by = admin_id

        self.db.commit()
        self.db.refresh(record)
        logger.info(
            "AI settings updated successfully by admin=%s, new version=%d",
            admin_id,
            record.config_version,
        )
        return record

    def get_options(self) -> AIOptionsResponse:
        settings = get_settings()
        groq_configured = bool(
            settings.groq_api_key and settings.groq_api_key.get_secret_value()
        )
        gemini_configured = bool(
            settings.gemini_api_key and settings.gemini_api_key.get_secret_value()
        )

        providers = [
            AIProviderOption(
                id="groq",
                name="Groq Cloud",
                models=sorted(VALID_MODELS_BY_PROVIDER["groq"]),
                is_configured=groq_configured,
            ),
            AIProviderOption(
                id="gemini",
                name="Google Gemini",
                models=sorted(VALID_MODELS_BY_PROVIDER["gemini"]),
                is_configured=gemini_configured,
            ),
        ]

        limits = {
            "jury_temperature": AIRangeLimit(min=0.0, max=1.0, step=0.05),
            "evaluation_temperature": AIRangeLimit(min=0.0, max=1.0, step=0.05),
            "jury_max_tokens": AIRangeLimit(min=256, max=4096, step=128),
            "max_followups": AIRangeLimit(min=0, max=5, step=1),
            "retrieval_top_k": AIRangeLimit(min=1, max=20, step=1),
        }

        return AIOptionsResponse(providers=providers, limits=limits)

    def _build_default_in_memory(self) -> AISettings:
        settings = get_settings()
        return AISettings(
            id=SINGLETON_SETTINGS_ID,
            jury_provider="groq",
            jury_model=settings.groq_question_model or "openai/gpt-oss-20b",
            jury_temperature=0.2,
            jury_max_tokens=2048,
            max_followups=2,
            retrieval_top_k=settings.question_retrieval_top_k or 4,
            evaluation_provider="groq",
            evaluation_model=settings.groq_question_model or "openai/gpt-oss-20b",
            evaluation_temperature=0.0,
            fallback_enabled=True,
            config_version=1,
            updated_at=datetime.now(UTC),
            updated_by=None,
        )
