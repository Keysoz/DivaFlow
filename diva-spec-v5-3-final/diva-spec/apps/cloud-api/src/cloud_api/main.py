"""Cloud API skeleton (TASK-P0-10). Endpoints arrive with their own tasks."""

from fastapi import FastAPI
from pydantic import BaseModel


class Health(BaseModel):
    """Liveness payload."""

    status: str


app = FastAPI(title="Diva Cloud API")


@app.get("/health")
def health() -> Health:
    """Report that the service is up."""
    return Health(status="ok")
