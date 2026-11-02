#!/usr/bin/env python3
"""Backfill Item.custom_barcode from the first Item Barcode (DEC-96).

The Item list shows the primary barcode from `custom_barcode`. Items created
before the hook kept that field have it empty while their barcodes live in the
Item Barcode child table, so the list column is blank. The server method copies
the first child barcode into `custom_barcode`; it is idempotent.

Usage (dev/staging only):
  ERPNEXT_URL=http://localhost:8080 ERPNEXT_USER=Administrator \
  ERPNEXT_PASSWORD=admin python3 scripts/backfill_item_barcodes.py
"""

from __future__ import annotations

import os
import sys

import httpx

BASE = os.environ.get("ERPNEXT_URL", "").rstrip("/")
USER = os.environ.get("ERPNEXT_USER", "")
PASSWORD = os.environ.get("ERPNEXT_PASSWORD", "")
if not (BASE and USER and PASSWORD):
    sys.exit("Set ERPNEXT_URL, ERPNEXT_USER and ERPNEXT_PASSWORD")

http = httpx.Client(base_url=BASE, timeout=120)
http.post("/api/method/login", data={"usr": USER, "pwd": PASSWORD}).raise_for_status()


def main() -> None:
    response = http.post("/api/method/diva_guard.item_list.backfill_primary_barcodes")
    if response.status_code >= 400:
        sys.exit(response.text[:400])
    updated = response.json().get("message")
    print(f"{updated} item(s) updated with their primary barcode")


if __name__ == "__main__":
    main()
