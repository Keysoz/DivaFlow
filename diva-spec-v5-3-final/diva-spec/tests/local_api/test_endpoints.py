"""Endpoint tests for the local API (TASK-E-12)."""

from collections.abc import Iterator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from local_api.deps import get_client
from local_api.main import app


class FakeErpNextClient:
    """In-memory stand-in for ErpNextClient used only in tests."""

    def __init__(self) -> None:
        self.barcodes: dict[str, list[dict[str, object]]] = {
            "P004-DOZEN": [
                {"name": "bc1", "barcode": "2100001000011", "uom": "Dozen"},
                {"name": "bc2", "barcode": "2100001000028", "uom": "Nos"},
            ],
            "BULK-ACC-01": [
                {"name": "bc3", "barcode": "2200000000016", "uom": "Dozen"},
            ],
        }

    def get_items(self, search: str | None = None, limit: int = 50) -> list[dict[str, object]]:
        rows = [
            {
                "name": "P004-DOZEN",
                "item_code": "P004-DOZEN",
                "item_name": "Diva Test Item",
                "item_group": "Accessories",
                "stock_uom": "Nos",
                "is_stock_item": 1,
                "has_batch_no": 0,
                "has_serial_no": 0,
                "description": "A test item",
            },
            {
                "name": "BULK-ACC-01",
                "item_code": "BULK-ACC-01",
                "item_name": "Bulk Accessories 01",
                "item_group": "Accessories",
                "stock_uom": "Nos",
                "is_stock_item": 1,
                "has_batch_no": 0,
                "has_serial_no": 0,
                "description": "Another test item",
            },
        ]
        if search:
            rows = [
                row
                for row in rows
                if search.lower() in str(row["item_code"]).lower()
                or search.lower() in str(row["item_name"]).lower()
            ]
        return rows[:limit]

    def get_item(self, item_code: str) -> dict[str, object]:
        if item_code not in ("P004-DOZEN", "BULK-ACC-01"):
            raise RuntimeError("not found")
        return {
            "name": item_code,
            "item_code": item_code,
            "item_name": "Diva Test Item" if item_code == "P004-DOZEN" else "Bulk Accessories 01",
            "item_group": "Accessories",
            "stock_uom": "Nos",
            "is_stock_item": 1,
            "has_batch_no": 0,
            "has_serial_no": 0,
            "description": "A test item",
            "barcodes": self.barcodes.get(item_code, []),
        }

    def get_item_prices(
        self, item_codes: list[str], price_list: str = "Standard Selling"
    ) -> dict[str, dict[str, Decimal]]:
        prices = {
            "P004-DOZEN": {"Dozen": Decimal("1440"), "Nos": Decimal("120")},
            "BULK-ACC-01": {"Dozen": Decimal("1200"), "Nos": Decimal("100")},
        }
        return {code: prices[code] for code in item_codes if code in prices}

    def get_bins(
        self, item_codes: list[str], warehouse: str | None = None
    ) -> dict[str, dict[str, Decimal]]:
        bins = {
            "P004-DOZEN": {"actual_qty": Decimal("60"), "reserved_qty": Decimal("24")},
            "BULK-ACC-01": {"actual_qty": Decimal("24"), "reserved_qty": Decimal("0")},
        }
        return {code: bins[code] for code in item_codes if code in bins}

    def get_barcodes(self, item_code: str) -> list[dict[str, object]]:
        return self.barcodes.get(item_code, [])

    def get_internal_barcodes(self) -> list[str]:
        return [
            *[str(row["barcode"]) for rows in self.barcodes.values() for row in rows],
            "2000000000015",
        ]

    def add_item_barcode(self, item_code: str, barcode: str, uom: str) -> None:
        self.barcodes.setdefault(item_code, []).append(
            {"name": f"new-{barcode}", "barcode": barcode, "uom": uom}
        )

    def get_item_by_barcode(self, barcode: str) -> dict[str, object] | None:
        """Return a fake item for a known barcode, None otherwise."""
        for item_code, rows in self.barcodes.items():
            if any(str(row["barcode"]) == barcode for row in rows):
                return {
                    "item_code": item_code,
                    "item_name": "Diva Test Item"
                    if item_code == "P004-DOZEN"
                    else "Bulk Accessories 01",
                    "stock_uom": "Nos",
                    "barcode_uom": next(
                        str(row["uom"]) for row in rows if str(row["barcode"]) == barcode
                    ),
                }
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


class TestOpsItems:
    """Items, barcodes and labels for the E-13 first slice."""

    def test_list_items_with_price_and_stock(self, client: TestClient) -> None:
        response = client.get("/api/items", headers=AUTH)
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 2
        first = next(row for row in rows if row["item_code"] == "P004-DOZEN")
        assert first["price_dozen"] == "1440"
        assert first["price_nos"] == "120"
        assert first["actual_qty"] == "60"
        assert first["reserved_qty"] == "24"

    def test_search_items(self, client: TestClient) -> None:
        response = client.get("/api/items", params={"search": "bulk"}, headers=AUTH)
        assert response.status_code == 200
        assert [row["item_code"] for row in response.json()] == ["BULK-ACC-01"]

    def test_item_detail_and_barcodes(self, client: TestClient) -> None:
        response = client.get("/api/items/P004-DOZEN", headers=AUTH)
        assert response.status_code == 200
        data = response.json()
        assert data["price_dozen"] == "1440"
        assert [row["uom"] for row in data["barcodes"]] == ["Dozen", "Nos"]

    def test_unknown_item_returns_404(self, client: TestClient) -> None:
        assert client.get("/api/items/NOPE", headers=AUTH).status_code == 404

    def test_label_for_dozen(self, client: TestClient) -> None:
        response = client.get(
            "/api/labels",
            params={"item_code": "P004-DOZEN", "uom": "Dozen", "copies": 2},
            headers=AUTH,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["barcode"] == "2100001000011"
        assert data["price"] == "1440"
        assert data["copies"] == 2
        assert data["ean13"] is True

    def test_label_without_uom_barcode_returns_404(self, client: TestClient) -> None:
        response = client.get(
            "/api/labels",
            params={"item_code": "BULK-ACC-01", "uom": "Nos"},
            headers=AUTH,
        )
        assert response.status_code == 404

    def test_generate_internal_barcode(self, client: TestClient) -> None:
        response = client.post(
            "/api/items/BULK-ACC-01/barcodes",
            json={"uom": "Nos"},
            headers=AUTH,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["generated"] is True
        assert data["uom"] == "Nos"
        assert data["barcode"].startswith("20")
        assert len(data["barcode"]) == 13

    def test_reject_duplicate_barcode(self, client: TestClient) -> None:
        response = client.post(
            "/api/items/BULK-ACC-01/barcodes",
            json={"barcode": "2100001000011", "uom": "Dozen"},
            headers=AUTH,
        )
        assert response.status_code == 409

    def test_reject_invalid_ean13(self, client: TestClient) -> None:
        response = client.post(
            "/api/items/BULK-ACC-01/barcodes",
            json={"barcode": "2100001000012", "uom": "Dozen"},
            headers=AUTH,
        )
        assert response.status_code == 422

    def test_ops_items_requires_token(self, client: TestClient) -> None:
        assert client.get("/api/items").status_code == 401
