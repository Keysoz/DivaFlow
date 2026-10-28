#!/usr/bin/env python3
"""Seed batch/expiry data for cosmetics and verify FEFO (TASK-E-14c).

Creates two batch-enabled cosmetics items with opening batches:
  BULK-COS-BATCH-01: one batch expiring soon, one later (FEFO picks the first).
  BULK-COS-EXPIRED-01: one already-expired batch (must not be sellable).

Idempotent: items/batches are created once; opening stock is posted only when no
stock ledger entry exists for the item. Synthetic data only.

Prerequisites: company "Diva Dev", item group "Cosmetics", warehouse
"Main Inventory - DD", accounts "Temporary Opening - DD" and cost center
"Main - DD". Credentials from the environment.
"""

import json
import os
import sys
from decimal import Decimal
from typing import Any, cast

import httpx

BASE = os.environ.get("ERPNEXT_URL", "").rstrip("/")
USER = os.environ.get("ERPNEXT_USER", "")
PASSWORD = os.environ.get("ERPNEXT_PASSWORD", "")
if not (BASE and USER and PASSWORD):
    sys.exit("Set ERPNEXT_URL, ERPNEXT_USER and ERPNEXT_PASSWORD")

COMPANY = "Diva Dev"
ABBR = "DD"
WAREHOUSE = f"Main Inventory - {ABBR}"
EXPENSE = f"Temporary Opening - {ABBR}"
COST_CENTER = f"Main - {ABBR}"
PRICE = 1200

http = httpx.Client(base_url=BASE, timeout=60)
http.post("/api/method/login", data={"usr": USER, "pwd": PASSWORD}).raise_for_status()


def get_list(doctype: str, filters: list[list[Any]], fields: list[str]) -> list[dict[str, Any]]:
    response = http.get(
        f"/api/resource/{doctype}",
        params={
            "filters": json.dumps(filters),
            "fields": json.dumps(fields),
            "limit_page_length": "0",
        },
    )
    response.raise_for_status()
    return response.json().get("data") or []


def create(doctype: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = http.post(f"/api/resource/{doctype}", json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"{doctype} create failed: {response.status_code} {response.text[:400]}")
    return cast(dict[str, Any], response.json()["data"])


def fetch(doctype: str, name: str) -> dict[str, Any]:
    response = http.get(f"/api/resource/{doctype}/{name}")
    response.raise_for_status()
    return cast(dict[str, Any], response.json()["data"])


def submit(doctype: str, name: str) -> None:
    doc = fetch(doctype, name)
    response = http.post("/api/method/frappe.client.submit", data={"doc": json.dumps(doc)})
    response.raise_for_status()


def ean13(base12: str) -> str:
    total = sum(int(digit) * (3 if index % 2 else 1) for index, digit in enumerate(base12))
    return base12 + str((10 - total % 10) % 10)


def ensure_item(code: str, name: str, barcode: str, shelf_life: int) -> None:
    if get_list("Item", [["name", "=", code]], ["name"]):
        return
    create(
        "Item",
        {
            "item_code": code,
            "item_name": name,
            "item_group": "Cosmetics",
            "stock_uom": "Nos",
            "is_stock_item": 1,
            "include_item_in_manufacturing": 0,
            "has_batch_no": 1,
            "create_new_batch": 1,
            "has_expiry_date": 1,
            "shelf_life_in_days": shelf_life,
            "uoms": [{"uom": "Dozen", "conversion_factor": 12}],
            "barcodes": [{"barcode": barcode, "barcode_type": "EAN", "uom": "Dozen"}],
        },
    )
    create(
        "Item Price",
        {
            "item_code": code,
            "price_list": "Standard Selling",
            "uom": "Dozen",
            "price_list_rate": PRICE,
            "selling": 1,
        },
    )


def ensure_batch(batch_id: str, item: str, expiry: str) -> None:
    if get_list("Batch", [["name", "=", batch_id]], ["name"]):
        return
    create(
        "Batch",
        {
            "batch_id": batch_id,
            "item": item,
            "expiry_date": expiry,
            "manufacturing_date": "2025-12-01",
        },
    )


def post_opening(item: str, rows: list[tuple[str, int]]) -> None:
    if get_list(
        "Stock Ledger Entry", [["item_code", "=", item], ["is_cancelled", "=", 0]], ["name"]
    ):
        return
    reconciliation = create(
        "Stock Reconciliation",
        {
            "company": COMPANY,
            "purpose": "Opening Stock",
            "posting_date": "2026-10-28",
            "posting_time": "09:00:00",
            "expense_account": EXPENSE,
            "cost_center": COST_CENTER,
            "items": [
                {
                    "item_code": item,
                    "warehouse": WAREHOUSE,
                    "qty": qty,
                    "batch_no": batch,
                    "use_serial_batch_fields": 1,
                    "valuation_rate": 100,
                }
                for batch, qty in rows
            ],
        },
    )
    submit("Stock Reconciliation", reconciliation["name"])


ensure_item("BULK-COS-BATCH-01", "Bulk Cosmetics Batch 01", ean13("210990000001"), 365)
ensure_batch("BATCH-COS-2026-00001", "BULK-COS-BATCH-01", "2026-11-15")
ensure_batch("BATCH-COS-2026-00002", "BULK-COS-BATCH-01", "2027-01-15")
post_opening("BULK-COS-BATCH-01", [("BATCH-COS-2026-00001", 24), ("BATCH-COS-2026-00002", 24)])

ensure_item("BULK-COS-EXPIRED-01", "Bulk Cosmetics Expired 01", ean13("210990000002"), 30)
ensure_batch("BATCH-EXP-2026-00001", "BULK-COS-EXPIRED-01", "2026-01-01")
post_opening("BULK-COS-EXPIRED-01", [("BATCH-EXP-2026-00001", 12)])

print("batch items ready")
for code in ("BULK-COS-BATCH-01", "BULK-COS-EXPIRED-01"):
    batches = get_list("Batch", [["item", "=", code]], ["name", "expiry_date", "batch_qty"])
    for batch in batches:
        print(
            code,
            batch["name"],
            "expiry",
            batch["expiry_date"],
            "qty",
            Decimal(str(batch["batch_qty"])),
        )
