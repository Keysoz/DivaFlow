#!/usr/bin/env python3
"""Verify opening quantity from Item quick entry (DEC-80)."""

import json
import os
import sys
import uuid

import httpx

BASE = os.environ.get("ERPNEXT_URL", "").rstrip("/")
USER = os.environ.get("ERPNEXT_USER", "")
PASSWORD = os.environ.get("ERPNEXT_PASSWORD", "")
if not (BASE and USER and PASSWORD):
    sys.exit("Set ERPNEXT_URL, ERPNEXT_USER and ERPNEXT_PASSWORD")

ITEM = f"BULK-QTY-{uuid.uuid4().hex[:8].upper()}"
BARCODE = f"QTY-{uuid.uuid4().hex[:10].upper()}"
failures = 0
http = httpx.Client(base_url=BASE, timeout=60)
http.post("/api/method/login", data={"usr": USER, "pwd": PASSWORD}).raise_for_status()


def check(label: str, ok: bool, detail: str = "") -> None:
    global failures
    print(("OK   " if ok else "FAIL ") + label + (f" — {detail}" if detail else ""))
    failures = failures + (0 if ok else 1)


def cleanup() -> None:
    for row in (
        http.get(
            "/api/resource/Stock Ledger Entry",
            params={
                "filters": json.dumps([["item_code", "=", ITEM]]),
                "fields": json.dumps(["voucher_type", "voucher_no"]),
                "limit_page_length": "0",
            },
        )
        .json()
        .get("data")
        or []
    ):
        if row["voucher_type"] == "Stock Reconciliation":
            http.post(
                "/api/method/frappe.client.cancel",
                data={"doctype": "Stock Reconciliation", "name": row["voucher_no"]},
            )
    for row in (
        http.get(
            "/api/resource/Item Price",
            params={
                "filters": json.dumps([["item_code", "=", ITEM]]),
                "fields": json.dumps(["name"]),
                "limit_page_length": "0",
            },
        )
        .json()
        .get("data")
        or []
    ):
        http.delete(f"/api/resource/Item Price/{row['name']}")
    http.delete(f"/api/resource/Item/{ITEM}")


cleanup()
field = (
    http.get(
        "/api/resource/Property Setter",
        params={
            "filters": json.dumps(
                [["doc_type", "=", "Item"], ["field_name", "=", "opening_stock"]]
            ),
            "fields": json.dumps(["property", "value"]),
            "limit_page_length": "0",
        },
    )
    .json()
    .get("data")
    or []
)
by_property = {row["property"]: str(row["value"]) for row in field}
check(
    "opening stock is visible on the Item form", by_property.get("hidden") == "0", str(by_property)
)
check(
    "opening stock is in quick entry",
    by_property.get("allow_in_quick_entry") == "1",
    str(by_property),
)

created = http.post(
    "/api/resource/Item",
    json={
        "item_code": ITEM,
        "item_name": "Bulk Quantity Test 01",
        "item_group": "Accessories",
        "stock_uom": "Nos",
        "custom_barcode": BARCODE,
        "standard_rate": 1200,
        "opening_stock": 24,
    },
)
check("item with opening quantity saves", created.status_code == 200, created.text[:200])
item = http.get(f"/api/resource/Item/{ITEM}").json().get("data") or {}
check(
    "opening quantity is stored",
    float(item.get("opening_stock") or 0) == 24,
    str(item.get("opening_stock")),
)
check(
    "valuation rate derived from the Dozen price",
    float(item.get("valuation_rate") or 0) == 100,
    str(item.get("valuation_rate")),
)

bins = (
    http.get(
        "/api/resource/Bin",
        params={
            "filters": json.dumps([["item_code", "=", ITEM]]),
            "fields": json.dumps(["warehouse", "actual_qty"]),
            "limit_page_length": "0",
        },
    )
    .json()
    .get("data")
    or []
)
check("stock quantity posted", any(float(row["actual_qty"]) == 24 for row in bins), str(bins))

prices = (
    http.get(
        "/api/resource/Item Price",
        params={
            "filters": json.dumps([["item_code", "=", ITEM]]),
            "fields": json.dumps(["uom", "price_list_rate"]),
            "limit_page_length": "0",
        },
    )
    .json()
    .get("data")
    or []
)
by_uom = {row["uom"]: float(row["price_list_rate"]) for row in prices}
check(
    "prices saved per Dozen and Nos",
    by_uom.get("Dozen") == 1200 and by_uom.get("Nos") == 100,
    str(by_uom),
)

cleanup()
http.close()
if failures:
    print("quick quantity checks FAILED")
raise SystemExit(1 if failures else 0)
