"""Dependencies for the local API."""

from collections.abc import Iterator

from fastapi import Depends

from erpnext_adapter import ErpNextClient
from local_api.settings import Settings, get_settings


def get_client(settings: Settings = Depends(get_settings)) -> Iterator[ErpNextClient]:
    client = ErpNextClient(
        settings.erpnext_url,
        api_key=settings.api_key,
        api_secret=settings.api_secret,
        username=settings.username,
        password=settings.password,
    )
    try:
        yield client
    finally:
        client.close()
