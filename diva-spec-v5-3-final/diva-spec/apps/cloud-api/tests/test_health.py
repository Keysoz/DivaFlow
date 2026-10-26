"""Tests for the Cloud API /health endpoint (TASK-P0-10)."""

from fastapi.testclient import TestClient

from cloud_api.main import app


def test_health_returns_200_with_ok_status() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
