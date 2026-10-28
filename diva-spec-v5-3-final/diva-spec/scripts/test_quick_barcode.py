#!/usr/bin/env python3
"""Verify the Item quick-entry barcode field (DEC-78, TASK-E-14a extension)."""

import json
import os
import sys

import httpx

BASE = os.environ.get("ERPNEXT_URL", "").rstrip("/")
USER = os.environ.get("ERPNEXT_USER", "")
PASSWORD = os.environ.get("ERPNEXT_PASSWORD", "")
if not (BASE and USER and PASSWORD):
    sys.exit("Set ERPNEXT_URL, ERPNEXT_USER and ERPNEXT_PASSWORD")

BARCODE = "2900000000019"
failures = 0

http = httpx.Client(base_url=BASE, timeout=60)
http.post("/api/method/login", data={"usr": USER, "pwd": PASSWORD}).raise_for_status()


def delete_item(code: str) -> None:
    http.delete(f"/api/resource/Item/{code}")


def create_item(code: str) -> httpx.Response:
    return http.post(
        "/api/resource/Item",
        json={
            "item_code": code,
            "item_name": f"Quick Barcode {code}",
            "item_group": "Accessories",
            "stock_uom": "Nos",
            "is_stock_item": 0,
            "custom_barcode": BARCODE,
            "standard_rate": 1200,
        },
    )


def check(label: str, ok: bool, detail: str = "") -> None:
    global failures
    print(("OK   " if ok else "FAIL ") + label + (f" — {detail}" if detail else ""))
    failures = failures + (0 if ok else 1)


field = (
    http.get(
        "/api/resource/Custom Field/Item-custom_barcode",
    )
    .json()
    .get("data")
    or {}
)
check(
    "custom field is in quick entry",
    bool(field.get("allow_in_quick_entry")) and field.get("insert_after") == "item_name",
    str(field.get("allow_in_quick_entry")),
)

for code in ("BULK-QB-01", "BULK-QB-02"):
    for row in (
        http.get(
            "/api/resource/Item Price",
            params={
                "filters": json.dumps([["item_code", "=", code]]),
                "fields": json.dumps(["name"]),
                "limit_page_length": "0",
            },
        )
        .json()
        .get("data")
        or []
    ):
        http.delete(f"/api/resource/Item Price/{row['name']}")
    delete_item(code)
first = create_item("BULK-QB-01")
check("item with quick barcode saves", first.status_code == 200, first.text[:160])
item = http.get("/api/resource/Item/BULK-QB-01").json().get("data") or {}
barcodes = [row.get("barcode") for row in item.get("barcodes") or []]
check("barcode moved to the Barcodes table", BARCODE in barcodes, str(barcodes))
rows = [row for row in item.get("barcodes") or [] if row.get("barcode") == BARCODE]
check("barcode UOM is the stock UOM", bool(rows) and rows[0].get("uom") == "Nos", str(rows))
check(
    "quick-entry field is cleared", not item.get("custom_barcode"), str(item.get("custom_barcode"))
)
prices = (
    http.get(
        "/api/resource/Item Price",
        params={
            "filters": json.dumps([["item_code", "=", "BULK-QB-01"]]),
            "fields": json.dumps(["name", "uom", "price_list_rate"]),
            "limit_page_length": "0",
        },
    )
    .json()
    .get("data")
    or []
)
by_uom = {row["uom"]: float(row["price_list_rate"]) for row in prices}
check(
    "quick price saved per Dozen and per Nos",
    by_uom.get("Dozen") == 1200 and by_uom.get("Nos") == 100,
    str(by_uom),
)

dozen = next((row for row in prices if row["uom"] == "Dozen"), None)
if dozen:
    http.put(
        f"/api/resource/Item Price/{dozen['name']}",
        json={"price_list_rate": 1250},
    )
unrelated = http.put(
    "/api/resource/Item/BULK-QB-01",
    json={"description": "Synthetic quick-entry test"},
)
check("unrelated Item save succeeds", unrelated.status_code == 200, unrelated.text[:160])
kept = {
    row["uom"]: float(row["price_list_rate"])
    for row in http.get(
        "/api/resource/Item Price",
        params={
            "filters": json.dumps([["item_code", "=", "BULK-QB-01"]]),
            "fields": json.dumps(["name", "uom", "price_list_rate"]),
            "limit_page_length": "0",
        },
    )
    .json()
    .get("data")
    or []
}
check(
    "unrelated Item save keeps a deliberate price edit",
    kept.get("Dozen") == 1250,
    str(kept),
)

resave = http.put(
    "/api/resource/Item/BULK-QB-01",
    json={"custom_barcode": BARCODE, "standard_rate": 1320},
)
check("re-saving the same barcode is idempotent", resave.status_code == 200, resave.text[:160])
after = http.get("/api/resource/Item/BULK-QB-01").json().get("data") or {}
check(
    "no duplicate child row",
    len([row for row in after.get("barcodes") or [] if row.get("barcode") == BARCODE]) == 1,
    str(after.get("barcodes")),
)
after_prices = (
    http.get(
        "/api/resource/Item Price",
        params={
            "filters": json.dumps([["item_code", "=", "BULK-QB-01"]]),
            "fields": json.dumps(["name", "uom", "price_list_rate"]),
            "limit_page_length": "0",
        },
    )
    .json()
    .get("data")
    or []
)
after_by_uom = {row["uom"]: float(row["price_list_rate"]) for row in after_prices}
check(
    "re-saving updates both prices",
    after_by_uom.get("Dozen") == 1320 and after_by_uom.get("Nos") == 110,
    str(after_by_uom),
)

second = create_item("BULK-QB-02")
check(
    "duplicate barcode is rejected",
    second.status_code >= 400 and "already" in second.text.lower(),
    second.text[:200],
)

for code in ("BULK-QB-01", "BULK-QB-02"):
    for row in (
        http.get(
            "/api/resource/Item Price",
            params={
                "filters": json.dumps([["item_code", "=", code]]),
                "fields": json.dumps(["name"]),
                "limit_page_length": "0",
            },
        )
        .json()
        .get("data")
        or []
    ):
        http.delete(f"/api/resource/Item Price/{row['name']}")
    delete_item(code)
http.close()
if failures:
    print("quick barcode checks FAILED")
raise SystemExit(1 if failures else 0)
