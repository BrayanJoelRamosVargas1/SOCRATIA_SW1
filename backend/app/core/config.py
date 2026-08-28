from functools import lru_cache
from pathlib import Path

from pydantic import EmailStr, Field, SecretStr, field_validator
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

    @field_validator("mail_from_email", mode="before")
    @classmethod
    def empty_sender_is_unconfigured(cls, value: object) -> object:
        return None if value == "" else value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_document_size_bytes(self) -> int:
        return self.max_document_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
