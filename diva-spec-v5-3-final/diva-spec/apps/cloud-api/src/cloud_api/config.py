"""Cloud API settings (TASK-PUB-01). Secrets come from the environment/secret manager."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "dev"
    database_url: str = "sqlite+pysqlite:///./diva.db"
    jwt_secret: SecretStr = SecretStr("dev-only-change-me-please-32-bytes-minimum")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 14
    mfa_issuer: str = "Diva"
    bootstrap_token: SecretStr = SecretStr("dev-bootstrap-token")
    cors_origins: list[str] = []

    def validate_for_runtime(self) -> None:
        if self.environment == "production":
            if self.jwt_secret.get_secret_value() == "dev-only-change-me-please-32-bytes-minimum":
                raise RuntimeError("JWT_SECRET must be set in production")
            if self.bootstrap_token.get_secret_value() == "dev-bootstrap-token":
                raise RuntimeError("BOOTSTRAP_TOKEN must be set in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
