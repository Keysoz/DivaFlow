"""Endpoint tests for the local API (TASK-E-12)."""

from collections.abc import Iterator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from local_api.deps import get_client
from local_api.main import app


class FakeErpNextClient:
    """In-memory stand-in for ErpNextClient used only in tests."""

    def get_item_by_barcode(self, barcode: str) -> dict[str, object] | None:
        """Return a fake item for barcode 2000000000015, None otherwise."""
        if barcode == "2000000000015":
            return {
                "item_code": "P004-DOZEN",
                "item_name": "Diva Test Item",
                "stock_uom": "Nos",
                "barcode_uom": "Dozen",
            }
        return None

    def get_price_list_rate(
        self, item_code: str, price_list: str, uom: str = "Dozen"
    ) -> Decimal | None:
        """Return 1440 for P004-DOZEN, None otherwise."""
        if item_code == "P004-DOZEN":
            return Decimal("1440")
        return None

    def get_bin(self, item_code: str, warehouse: str | None = None) -> dict[str, object]:
        """Return stock data for P004-DOZEN."""
        if item_code == "P004-DOZEN":
            return {"actual_qty": 60, "reserved_qty": 24, "stock_uom": "Nos"}
        return {"actual_qty": 0, "reserved_qty": 0}


def _fake_get_client() -> Iterator[FakeErpNextClient]:
    """Dependency override for get_client."""
    yield FakeErpNextClient()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """TestClient with auth token set and a fake ERPNext client."""
    monkeypatch.setenv("LOCAL_API_TOKEN", "test-token")
    app.dependency_overrides[get_client] = _fake_get_client
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


AUTH = {"Authorization": "Bearer test-token"}


class TestHealth:
    """GET /health requires no authentication."""

    def test_health_returns_200_without_auth(self, client: TestClient) -> None:
        """Health endpoint is public and returns ok status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestItemByBarcode:
    """GET /api/items/by-barcode/{barcode} requires bearer token."""

    def test_known_barcode_with_token(self, client: TestClient) -> None:
        """Valid barcode and token returns item data."""
        response = client.get("/api/items/by-barcode/2000000000015", headers=AUTH)
        assert response.status_code == 200
        data = response.json()
        assert data["item_code"] == "P004-DOZEN"
        assert data["item_name"] == "Diva Test Item"
        assert data["stock_uom"] == "Nos"
        assert data["barcode_uom"] == "Dozen"
        assert data["price_dozen"] == "1440"
        assert data["actual_qty"] == "60"
        assert data["reserved_qty"] == "24"

    def test_without_token_returns_401(self, client: TestClient) -> None:
        """Missing bearer token returns 401."""
        response = client.get("/api/items/by-barcode/2000000000015")
        assert response.status_code == 401

    def test_unknown_barcode_returns_404(self, client: TestClient) -> None:
        """Unknown barcode returns 404."""
        response = client.get("/api/items/by-barcode/9999999999999", headers=AUTH)
        assert response.status_code == 404


class TestEvaluateCounter:
    """POST /api/rules/counter/evaluate runs counter rules."""

    def test_cashier_seven_percent_requires_manager(self, client: TestClient) -> None:
        """Cashier with 7% discount requires manager approval."""
        body = {
            "role": "cashier",
            "lines": [
                {
                    "item_code": "P004-DOZEN",
                    "qty_dozens": "5",
                    "price_list_rate": "1000",
                    "net_rate": "930",
                }
            ],
        }
        response = client.post("/api/rules/counter/evaluate", json=body, headers=AUTH)
        assert response.status_code == 200
        data = response.json()
        assert data["requires_manager"] is True
        rules = [v["rule"] for v in data["violations"]]
        assert "discount_manager_required" in rules

    def test_manager_seven_percent_no_manager_violation(self, client: TestClient) -> None:
        """Manager with 7% discount has requires_manager but no violation."""
        body = {
            "role": "manager",
            "lines": [
                {
                    "item_code": "P004-DOZEN",
                    "qty_dozens": "5",
                    "price_list_rate": "1000",
                    "net_rate": "930",
                }
            ],
        }
        response = client.post("/api/rules/counter/evaluate", json=body, headers=AUTH)
        assert response.status_code == 200
        data = response.json()
        assert data["requires_manager"] is True
        rules = [v["rule"] for v in data["violations"]]
        assert "discount_manager_required" not in rules
        assert data["ok"] is True

    def test_over_fifteen_percent_discount_limit(self, client: TestClient) -> None:
        """Discount >15% violates discount_limit."""
        body = {
            "role": "manager",
            "lines": [
                {
                    "item_code": "P004-DOZEN",
                    "qty_dozens": "5",
                    "price_list_rate": "1000",
                    "net_rate": "800",
                }
            ],
        }
        response = client.post("/api/rules/counter/evaluate", json=body, headers=AUTH)
        assert response.status_code == 200
        data = response.json()
        rules = [v["rule"] for v in data["violations"]]
        assert "discount_limit" in rules
        assert data["ok"] is False

    def test_moq_below_minimum(self, client: TestClient) -> None:
        """Quantity below minimum triggers moq_min violation."""
        body = {
            "role": "cashier",
            "lines": [
                {
                    "item_code": "P004-DOZEN",
                    "qty_dozens": "2",
                    "min_qty": "5",
                    "price_list_rate": "1000",
                    "net_rate": "1000",
                }
            ],
        }
        response = client.post("/api/rules/counter/evaluate", json=body, headers=AUTH)
        assert response.status_code == 200
        data = response.json()
        rules = [v["rule"] for v in data["violations"]]
        assert "moq_min" in rules
        assert data["ok"] is False

    def test_empty_lines_returns_422(self, client: TestClient) -> None:
        """Empty lines array returns 422 validation error."""
        body = {"role": "cashier", "lines": []}
        response = client.post("/api/rules/counter/evaluate", json=body, headers=AUTH)
        assert response.status_code == 422
