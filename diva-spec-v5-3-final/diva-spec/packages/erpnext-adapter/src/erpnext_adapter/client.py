"""Typed ERPNext REST client (TASK-E-12)."""

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
            "/api/method/frappe.client.submit", data={"doc": __import__("json").dumps(created)}
        )
        if submit.status_code >= 400:
            raise ErpNextError(f"submit {doctype} failed: {submit.status_code} {submit.text[:200]}")
        return cast(dict[str, object], submit.json()["message"])
