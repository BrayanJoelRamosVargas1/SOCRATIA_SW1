from functools import lru_cache
from pathlib import Path

from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Socratia API"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://socratia:socratia_dev_password@localhost:5432/socratia"

    jwt_secret: str = "change-this-development-secret-before-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=15, ge=1, le=1440)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=90)
    login_ip_max_attempts: int = Field(default=20, ge=5, le=500)
    login_ip_window_seconds: int = Field(default=60, ge=10, le=3600)
    trust_proxy_headers: bool = False
    password_reset_token_ttl_minutes: int = Field(default=15, ge=5, le=60)
    password_reset_max_requests_per_identifier: int = Field(default=3, ge=1, le=20)
    password_reset_max_requests_per_ip: int = Field(default=10, ge=1, le=100)
    password_reset_rate_window_seconds: int = Field(default=3600, ge=60, le=86400)

    frontend_url: str = "http://localhost:3000"
    smtp_host: str = "smtp-relay.brevo.com"
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_starttls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: int = Field(default=15, ge=1, le=60)
    mail_from_name: str = "Socratia"
    mail_from_email: EmailStr | None = None

    access_cookie_name: str = "socratia_access"
    refresh_cookie_name: str = "socratia_refresh"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cors_origins: str = "http://localhost:3000"
    local_storage_path: Path = Path("./uploads")
    max_document_size_mb: int = Field(default=20, ge=1, le=100)

    embedding_provider: str = "gemini"
    gemini_api_key: SecretStr | None = None
    gemini_embedding_model: str = "gemini-embedding-2"
    embedding_dimensions: int = Field(default=768, ge=128, le=3072)
    embedding_batch_size: int = Field(default=20, ge=1, le=100)
    embedding_timeout_seconds: int = Field(default=60, ge=5, le=300)

    vector_primary_provider: str = "pinecone"
    pinecone_api_key: SecretStr | None = None
    pinecone_index_name: str = "socratia-documents"
    pinecone_namespace_prefix: str = "socratia"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    pinecone_timeout_seconds: int = Field(default=60, ge=5, le=300)

    question_retrieval_top_k: int = Field(default=4, ge=1, le=20)
    question_context_max_chars: int = Field(default=45000, ge=3000, le=120000)
    question_generation_timeout_seconds: int = Field(default=90, ge=10, le=300)
    question_generation_max_attempts: int = Field(default=2, ge=1, le=3)
    gemini_question_max_output_tokens: int = Field(default=8192, ge=2048, le=16384)
    groq_question_max_output_tokens: int = Field(default=4096, ge=2048, le=8192)
    question_circuit_breaker_threshold: int = Field(default=3, ge=1, le=20)
    question_circuit_breaker_recovery_seconds: int = Field(default=60, ge=5, le=3600)
    gemini_question_model: str = "gemini-2.5-flash"
    groq_question_model: str = "openai/gpt-oss-20b"
    groq_question_max_context_chars: int = Field(default=10000, ge=3000, le=60000)

    document_chunk_size_chars: int = Field(default=3000, ge=500, le=12000)
    document_chunk_overlap_chars: int = Field(default=400, ge=0, le=3000)
    document_max_chunks: int = Field(default=500, ge=1, le=5000)

    groq_api_key: SecretStr | None = None
    groq_live_model: str | None = None
    groq_stt_model: str = "whisper-large-v3-turbo"

    @field_validator("mail_from_email", mode="before")
    @classmethod
    def empty_sender_is_unconfigured(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator(
        "gemini_api_key",
        "pinecone_api_key",
        "groq_api_key",
        "groq_live_model",
        mode="before",
    )
    @classmethod
    def empty_provider_value_is_unconfigured(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def validate_document_chunking(self) -> "Settings":
        if self.document_chunk_overlap_chars >= self.document_chunk_size_chars:
            raise ValueError("DOCUMENT_CHUNK_OVERLAP_CHARS must be smaller than chunk size")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_document_size_bytes(self) -> int:
        return self.max_document_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
