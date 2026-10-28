#!/usr/bin/env python3
"""Verify FEFO and expired-batch blocking on the dev site (TASK-E-14c, TEST-10)."""

import json
import os
import sys
from typing import Any, cast

import httpx

BASE = os.environ.get("ERPNEXT_URL", "").rstrip("/")
ADMIN_USER = os.environ.get("ERPNEXT_USER", "")
ADMIN_PASSWORD = os.environ.get("ERPNEXT_PASSWORD", "")
TEST_PASSWORD = os.environ.get("DIVA_TEST_PASSWORD", "")
if not (BASE and ADMIN_USER and ADMIN_PASSWORD and TEST_PASSWORD):
    sys.exit("Set ERPNEXT_URL, ERPNEXT_USER, ERPNEXT_PASSWORD and DIVA_TEST_PASSWORD")

COMPANY = "Diva Dev"
CUSTOMER = "Bulk Customer 01"
WAREHOUSE = "Main Inventory - DD"
BATCH_ITEM = "BULK-COS-BATCH-01"
EXPIRED_ITEM = "BULK-COS-EXPIRED-01"

admin = httpx.Client(base_url=BASE, timeout=60)
admin.post("/api/method/login", data={"usr": ADMIN_USER, "pwd": ADMIN_PASSWORD}).raise_for_status()
cashier = httpx.Client(base_url=BASE, timeout=60)
cashier.post(
    "/api/method/login", data={"usr": "cashier@diva.test", "pwd": TEST_PASSWORD}
).raise_for_status()


def get_list(
    client: httpx.Client, doctype: str, filters: list[list[Any]], fields: list[str]
) -> list[dict[str, Any]]:
    response = client.get(
        f"/api/resource/{doctype}",
        params={
            "filters": json.dumps(filters),
            "fields": json.dumps(fields),
            "limit_page_length": "0",
        },
    )
    response.raise_for_status()
    return response.json().get("data") or []


def payload(item: str, qty: float, rate: float) -> dict[str, Any]:
    return {
        "is_pos": 1,
        "pos_profile": "P003 POS",
        "customer": CUSTOMER,
        "company": COMPANY,
        "currency": "EGP",
        "conversion_rate": 1,
        "update_stock": 1,
        "selling_price_list": "Standard Selling",
        "price_list_currency": "EGP",
        "plc_conversion_rate": 1,
        "remarks": "E-14c FEFO test",
        "items": [
            {"item_code": item, "qty": qty, "uom": "Nos", "warehouse": WAREHOUSE, "rate": rate}
        ],
        "payments": [{"mode_of_payment": "Cash", "amount": qty * rate}],
    }


def create(client: httpx.Client, body: dict[str, Any]) -> httpx.Response:
    return client.post("/api/resource/Sales Invoice", json=body)


def message(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text
    return str(data.get("_server_messages") or data.get("exception") or data)[:400]


def submit(client: httpx.Client, name: str) -> httpx.Response:
    doc = client.get(f"/api/resource/Sales Invoice/{name}").json()["data"]
    return client.post("/api/method/frappe.client.submit", data={"doc": json.dumps(doc)})


failed = False

batches = get_list(
    admin,
    "Batch",
    [["item", "=", BATCH_ITEM], ["batch_qty", ">", 0]],
    ["name", "expiry_date", "batch_qty"],
)
if not batches:
    print("FAIL no available batches; run scripts/seed_batches.py first")
    raise SystemExit(1)
expected = min(batches, key=lambda row: row["expiry_date"] or "9999-12-31")
print(
    "available batches:", [(row["name"], row["expiry_date"], row["batch_qty"]) for row in batches]
)
print("expected FEFO batch:", expected["name"])

response = create(cashier, payload(BATCH_ITEM, 1, 100))
print("create FEFO sale:", response.status_code, message(response)[:160])
if response.status_code != 200:
    failed = True
else:
    name = response.json()["data"]["name"]
    submitted = submit(cashier, name)
    print("submit FEFO sale:", submitted.status_code, message(submitted)[:160])
    if submitted.status_code != 200:
        failed = True
    else:
        ledger = get_list(
            admin,
            "Stock Ledger Entry",
            [["voucher_no", "=", name], ["is_cancelled", "=", 0]],
            ["serial_and_batch_bundle", "actual_qty"],
        )
        bundle_name = ledger[0].get("serial_and_batch_bundle") if ledger else None
        entries = (
            admin.get(f"/api/resource/Serial and Batch Bundle/{bundle_name}")
            .json()["data"]
            .get("entries")
            if bundle_name
            else []
        )
        selected = cast(list[dict[str, Any]], entries or [])
        chosen = selected[0].get("batch_no") if selected else None
        ok = chosen == expected["name"] and selected[0].get("qty") == -1
        print(("OK   " if ok else "FAIL ") + f"FEFO picked {chosen} (expected {expected['name']})")
        failed = failed or not ok
    admin.post("/api/method/frappe.client.cancel", data={"doctype": "Sales Invoice", "name": name})
    admin.delete(f"/api/resource/Sales Invoice/{name}")

expired = create(cashier, payload(EXPIRED_ITEM, 1, 100))
print("create expired sale:", expired.status_code, message(expired)[:200])
if expired.status_code != 200:
    print("OK   expired batch cannot be added")
elif expired.json()["data"]:
    name = expired.json()["data"]["name"]
    submitted = submit(cashier, name)
    blocked = submitted.status_code != 200 and "batch" in message(submitted).lower()
    print(
        ("OK   " if blocked else "FAIL ")
        + f"expired batch blocked on submit ({submitted.status_code})"
    )
    failed = failed or not blocked
    admin.delete(f"/api/resource/Sales Invoice/{name}")
else:
    failed = True

cashier.close()
admin.close()
if failed:
    print("E-14c FEFO checks FAILED")
raise SystemExit(1 if failed else 0)
