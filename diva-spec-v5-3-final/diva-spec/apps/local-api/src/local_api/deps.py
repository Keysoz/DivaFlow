"""Dependencies for the local API."""

from functools import lru_cache

from fastapi import Depends

from erpnext_adapter import ErpNextClient
from local_api.settings import Settings, get_settings


@lru_cache
def _build_client(settings: Settings) -> ErpNextClient:
    return ErpNextClient(
        settings.erpnext_url,
        api_key=settings.api_key,
        api_secret=settings.api_secret,
        username=settings.username,
        password=settings.password,
    )


def get_client(settings: Settings = Depends(get_settings)) -> ErpNextClient:
    """Reuse one client per settings; session login is not repeated per request."""
    return _build_client(settings)
