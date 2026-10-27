"""Environment settings for the local API (credentials from env, never hard-coded)."""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    erpnext_url: str
    api_key: str | None
    api_secret: str | None
    username: str | None
    password: str | None
    api_token: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            erpnext_url=os.environ.get("ERPNEXT_URL", "http://localhost:8080"),
            api_key=os.environ.get("ERPNEXT_API_KEY"),
            api_secret=os.environ.get("ERPNEXT_API_SECRET"),
            username=os.environ.get("ERPNEXT_USER"),
            password=os.environ.get("ERPNEXT_PASSWORD"),
            api_token=os.environ.get("LOCAL_API_TOKEN"),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
