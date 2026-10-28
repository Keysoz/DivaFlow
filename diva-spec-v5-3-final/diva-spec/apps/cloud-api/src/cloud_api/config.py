"""Cloud API settings (TASK-PUB-01). Secrets come from the environment/secret manager."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "dev"
    database_url: str = "sqlite+pysqlite:///./diva.db"
    jwt_secret: SecretStr = SecretStr("dev-only-change-me-please-32-bytes-minimum")
    mfa_encryption_key: SecretStr = SecretStr("dev-mfa-key-change-me-32-bytes-minimum")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 14
    mfa_issuer: str = "Diva"
    bootstrap_token: SecretStr = SecretStr("dev-bootstrap-token")
    cors_origins: list[str] = []
    trusted_proxies: list[str] = []
    audit_retention_days: int = 365

    def validate_for_runtime(self) -> None:
        if self.environment not in {"dev", "staging", "production"}:
            raise RuntimeError("ENVIRONMENT must be dev, staging or production")
        if self.environment != "dev":
            if self.jwt_secret.get_secret_value() == "dev-only-change-me-please-32-bytes-minimum":
                raise RuntimeError("JWT_SECRET must be set outside dev")
            if (
                self.mfa_encryption_key.get_secret_value()
                == "dev-mfa-key-change-me-32-bytes-minimum"
            ):
                raise RuntimeError("MFA_ENCRYPTION_KEY must be set outside dev")
            if self.bootstrap_token.get_secret_value() == "dev-bootstrap-token":
                raise RuntimeError("BOOTSTRAP_TOKEN must be set outside dev")
        if len(self.jwt_secret.get_secret_value()) < 32:
            raise RuntimeError("JWT_SECRET must be at least 32 bytes")
        if len(self.mfa_encryption_key.get_secret_value()) < 32:
            raise RuntimeError("MFA_ENCRYPTION_KEY must be at least 32 bytes")


@lru_cache
def get_settings() -> Settings:
    return Settings()
