#!/usr/bin/env python3
"""Checks for the staff Product Info page endpoint (DEC-95).

Resolves an item by code and by barcode, and checks the card fields: name,
group, barcode, image, Standard Selling Dozen/Nos prices, total stock and the
warehouse breakdown.

Usage:
  ERPNEXT_URL=http://localhost:8080 ERPNEXT_USER=Administrator \
  ERPNEXT_PASSWORD=admin python3 scripts/test_product_info.py
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, cast

import httpx

BASE = os.environ.get("ERPNEXT_URL", "").rstrip("/")
USER = os.environ.get("ERPNEXT_USER", "")
PASSWORD = os.environ.get("ERPNEXT_PASSWORD", "")
if not (BASE and USER and PASSWORD):
    sys.exit("Set ERPNEXT_URL, ERPNEXT_USER and ERPNEXT_PASSWORD")

COMPANY = "Diva Dev"
ITEM = "BULK-ACC-01"
BARCODE = "2100001000011"
STAMP = time.strftime("%H%M%S")
IMAGE_ITEM = f"PINFO-{STAMP}"

failures = 0
created: list[tuple[str, str]] = []

http = httpx.Client(base_url=BASE, timeout=60)
http.post("/api/method/login", data={"usr": USER, "pwd": PASSWORD}).raise_for_status()


def expect(label: str, condition: Any, detail: Any = "") -> bool:
    global failures
    ok = bool(condition)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -> {detail}"))
    if not ok:
        failures += 1
    return ok


def lookup(query: str) -> dict[str, Any]:
    response = http.post("/api/method/diva_guard.product_info.product_info", data={"query": query})
    if response.status_code >= 400:
        raise RuntimeError(response.text[:400])
    return cast(dict[str, Any], response.json()["message"])


def create(doctype: str, payload: dict[str, Any]) -> str:
    response = http.post(f"/api/resource/{doctype}", json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"create {doctype}: {response.text[:300]}")
    name = str(response.json()["data"]["name"])
    created.append((doctype, name))
    return name


def main() -> None:
    print("\n1. Resolve by item code and by barcode")
    by_code = lookup(ITEM)
    expect("item code resolves to a card", by_code.get("matched") is True, by_code)
    item = by_code.get("item") or {}
    expect(
        "code and name are returned",
        item.get("item_code") == ITEM and bool(item.get("item_name")),
        item,
    )
    expect("item group is returned", bool(item.get("item_group")), item)
    expect("barcode is returned", bool(item.get("barcode")), item.get("barcode"))
    expect(
        "Standard Selling Dozen price is returned",
        item.get("price_dozen") is not None,
        item.get("price_dozen"),
    )
    expect(
        "Standard Selling Nos price is returned",
        item.get("price_nos") is not None,
        item.get("price_nos"),
    )
    expect(
        "total stock is returned", float(item.get("total_stock") or 0) > 0, item.get("total_stock")
    )
    bins = item.get("bins") or []
    expect(
        "warehouse stock is returned",
        bool(bins) and all(bin.get("warehouse") for bin in bins),
        bins,
    )
    expect(
        "barcodes resolve to the same item",
        lookup(BARCODE).get("item", {}).get("item_code") == ITEM,
        lookup(BARCODE),
    )

    print("\n2. Product image and unmatched search")
    image_item = create(
        "Item",
        {
            "item_code": IMAGE_ITEM,
            "item_name": f"Product Info {STAMP}",
            "item_group": "Accessories",
            "stock_uom": "Nos",
            "is_stock_item": 1,
            "image": "/files/test-product.png",
            "standard_rate": 120,
        },
    )
    image_card = lookup(image_item).get("item") or {}
    expect(
        "product image URL is returned when present",
        str(image_card.get("image") or "").endswith("/files/test-product.png"),
        image_card.get("image"),
    )
    unmatched = lookup("no-such-item-zzz-999")
    expect("unknown text returns no match", unmatched.get("matched") is False, unmatched)
    expect("unknown text returns an empty match list", "matches" in unmatched, unmatched)
    fuzzy = lookup("Bulk Accessories")
    expect("a name search returns matches", bool(fuzzy.get("matches")), fuzzy)


def cleanup() -> None:
    for doctype, name in reversed(created):
        try:
            http.delete(f"/api/resource/{doctype}/{name}")
        except Exception as error:  # noqa: BLE001 - cleanup must never hide the result
            print(f"cleanup skipped for {doctype} {name}: {error}")


if __name__ == "__main__":
    try:
        main()
    finally:
        cleanup()
    print(f"\n{'FAILURES: ' + str(failures) if failures else 'all product info checks passed'}")
    sys.exit(1 if failures else 0)
