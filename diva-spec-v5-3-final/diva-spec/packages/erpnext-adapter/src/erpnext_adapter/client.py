"""Typed ERPNext REST client (TASK-E-12)."""

import json
from decimal import Decimal
from typing import Any, cast

import httpx


class ErpNextError(RuntimeError):
    """An ERPNext call failed."""


class ErpNextClient:
    """Thin typed client over the ERPNext REST API (session or API-token auth)."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        api_secret: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(base_url=self.base_url, timeout=timeout)
        if api_key and api_secret:
            self._http.headers["Authorization"] = f"token {api_key}:{api_secret}"
        elif username and password:
            response = self._http.post("/api/method/login", data={"usr": username, "pwd": password})
            if response.status_code != 200:
                raise ErpNextError(f"login failed: {response.status_code}")
        else:
            raise ValueError("provide api_key/api_secret or username/password")

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "ErpNextClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        response = self._http.get(path, params=params)
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise ErpNextError(f"GET {path} failed: {response.status_code} {response.text[:200]}")
        return response.json()

    def _put(self, path: str, payload: dict[str, object]) -> Any:
        response = self._http.put(path, json=payload)
        if response.status_code >= 400:
            raise ErpNextError(f"PUT {path} failed: {response.status_code} {response.text[:200]}")
        return response.json() if response.content else {}

    def ping(self) -> bool:
        payload = self._get("/api/method/ping")
        return isinstance(payload, dict) and payload.get("message") == "pong"

    def get_item(self, item_code: str) -> dict[str, object]:
        payload = self._get(f"/api/resource/Item/{item_code}")
        if payload is None:
            raise ErpNextError(f"item not found: {item_code}")
        return cast(dict[str, object], payload["data"])

    def get_item_by_barcode(self, barcode: str) -> dict[str, object] | None:
        filters = [["barcode", "=", barcode]]
        payload = self._get(
            "/api/resource/Item Barcode",
            {
                "filters": str(filters).replace("'", '"'),
                "fields": '["name"]',
                "limit_page_length": "1",
            },
        )
        rows = (payload or {}).get("data") or []
        if not rows:
            return None
        # Child tables ignore the fields selection; read the row by name.
        row = self._get("/api/resource/Item Barcode/" + str(rows[0]["name"]))
        if row is None:
            return None
        data = row["data"]
        item = self.get_item(str(data["parent"]))
        item["barcode_uom"] = data.get("uom")
        return item

    def get_price_list_rate(
        self, item_code: str, price_list: str, uom: str = "Dozen"
    ) -> Decimal | None:
        filters = [
            ["item_code", "=", item_code],
            ["price_list", "=", price_list],
            ["uom", "=", uom],
        ]
        payload = self._get(
            "/api/resource/Item Price",
            {
                "filters": str(filters).replace("'", '"'),
                "fields": '["price_list_rate"]',
                "limit_page_length": "1",
            },
        )
        rows = (payload or {}).get("data") or []
        if not rows:
            return None
        return Decimal(str(rows[0]["price_list_rate"]))

    def get_bin(self, item_code: str, warehouse: str | None = None) -> dict[str, object]:
        filters = [["item_code", "=", item_code]]
        if warehouse:
            filters.append(["warehouse", "=", warehouse])
        payload = self._get(
            "/api/resource/Bin",
            {
                "filters": str(filters).replace("'", '"'),
                "fields": '["warehouse","actual_qty","reserved_qty","stock_uom"]',
                "limit_page_length": "1",
            },
        )
        rows = (payload or {}).get("data") or []
        return cast(dict[str, object], rows[0]) if rows else {"actual_qty": 0, "reserved_qty": 0}

    def get_items(self, search: str | None = None, limit: int = 50) -> list[dict[str, object]]:
        """List active items for the Ops Items screen (TASK-E-13)."""
        params = {
            "filters": json.dumps([["disabled", "=", 0]]),
            "fields": json.dumps(
                [
                    "name",
                    "item_code",
                    "item_name",
                    "item_group",
                    "stock_uom",
                    "is_stock_item",
                    "has_batch_no",
                    "has_serial_no",
                    "description",
                    "image",
                    "standard_rate",
                ]
            ),
            "limit_page_length": str(limit),
            "order_by": "modified desc",
        }
        if search:
            params["or_filters"] = json.dumps(
                [
                    ["item_code", "like", f"%{search}%"],
                    ["item_name", "like", f"%{search}%"],
                    ["description", "like", f"%{search}%"],
                ]
            )
        payload = self._get("/api/resource/Item", params)
        return cast(list[dict[str, object]], (payload or {}).get("data") or [])

    def get_item_prices(
        self, item_codes: list[str], price_list: str = "Standard Selling"
    ) -> dict[str, dict[str, Decimal]]:
        """Return {item_code: {uom: price}} for the requested items."""
        if not item_codes:
            return {}
        payload = self._get(
            "/api/resource/Item Price",
            {
                "filters": json.dumps(
                    [["item_code", "in", item_codes], ["price_list", "=", price_list]]
                ),
                "fields": json.dumps(["item_code", "uom", "price_list_rate"]),
                "limit_page_length": "0",
            },
        )
        prices: dict[str, dict[str, Decimal]] = {}
        for row in (payload or {}).get("data") or []:
            item_code = str(row["item_code"])
            prices.setdefault(item_code, {})[str(row["uom"])] = Decimal(str(row["price_list_rate"]))
        return prices

    def get_bins(
        self, item_codes: list[str], warehouse: str | None = None
    ) -> dict[str, dict[str, Decimal]]:
        """Return {item_code: {actual_qty, reserved_qty}} summed over bins."""
        if not item_codes:
            return {}
        filters: list[list[object]] = [["item_code", "in", item_codes]]
        if warehouse:
            filters.append(["warehouse", "=", warehouse])
        payload = self._get(
            "/api/resource/Bin",
            {
                "filters": json.dumps(filters),
                "fields": json.dumps(["item_code", "actual_qty", "reserved_qty"]),
                "limit_page_length": "0",
            },
        )
        totals: dict[str, dict[str, Decimal]] = {}
        for row in (payload or {}).get("data") or []:
            item_code = str(row["item_code"])
            bucket = totals.setdefault(
                item_code, {"actual_qty": Decimal("0"), "reserved_qty": Decimal("0")}
            )
            bucket["actual_qty"] += Decimal(str(row.get("actual_qty") or 0))
            bucket["reserved_qty"] += Decimal(str(row.get("reserved_qty") or 0))
        return totals

    def _child_rows(self, names: list[str]) -> list[dict[str, object]]:
        """Read Item Barcode rows by name.

        Frappe ignores the ``fields`` selection when listing a child table and
        returns only the row name, so each row is fetched individually.
        """
        rows: list[dict[str, object]] = []
        for name in names:
            payload = self._get("/api/resource/Item Barcode/" + name)
            if payload and payload.get("data"):
                rows.append(cast(dict[str, object], payload["data"]))
        return rows

    def get_barcodes(self, item_code: str) -> list[dict[str, object]]:
        """Return the barcode rows of one Item."""
        payload = self._get(
            "/api/resource/Item Barcode",
            {
                "filters": json.dumps([["parent", "=", item_code]]),
                "fields": json.dumps(["name"]),
                "limit_page_length": "0",
            },
        )
        names = [str(row["name"]) for row in (payload or {}).get("data") or []]
        return self._child_rows(names)

    def get_internal_barcodes(self) -> list[str]:
        """Return all barcodes in the GS1 in-store range 20-29."""
        payload = self._get(
            "/api/resource/Item Barcode",
            {
                "filters": json.dumps([["barcode", "like", "2%"]]),
                "fields": json.dumps(["name"]),
                "limit_page_length": "0",
            },
        )
        names = [str(row["name"]) for row in (payload or {}).get("data") or []]
        return [str(row["barcode"]) for row in self._child_rows(names) if row.get("barcode")]

    def add_item_barcode(self, item_code: str, barcode: str, uom: str) -> None:
        """Add a barcode row to an Item, preserving the existing rows."""
        item = self.get_item(item_code)
        rows: list[dict[str, object]] = []
        for row in cast(list[dict[str, object]], item.get("barcodes") or []):
            rows.append({key: row[key] for key in ("name", "barcode", "uom") if key in row})
        if any(str(row.get("barcode")) == barcode for row in rows):
            raise ErpNextError(f"barcode already exists on {item_code}: {barcode}")
        rows.append({"barcode": barcode, "uom": uom})
        self._put(f"/api/resource/Item/{item_code}", {"barcodes": rows})

    def get_customer(self, name: str) -> dict[str, object] | None:
        payload = self._get(f"/api/resource/Customer/{name}")
        return None if payload is None else cast(dict[str, object], payload["data"])

    def submit_document(self, doctype: str, doc: dict[str, object]) -> dict[str, object]:
        response = self._http.post(f"/api/resource/{doctype}", json=doc)
        if response.status_code >= 400:
            raise ErpNextError(
                f"create {doctype} failed: {response.status_code} {response.text[:200]}"
            )
        created = response.json()["data"]
        submit = self._http.post(
            "/api/method/frappe.client.submit", data={"doc": json.dumps(created)}
        )
        if submit.status_code >= 400:
            raise ErpNextError(f"submit {doctype} failed: {submit.status_code} {submit.text[:200]}")
        return cast(dict[str, object], submit.json()["message"])
