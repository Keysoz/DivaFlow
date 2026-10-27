#!/usr/bin/env python3
"""Generate docs/erp-field-register.csv from a live ERPNext site.

Reads both the source schema (DocField) and the installed Custom Field rows, so
vendor fields (for example POS Next) are included. Every row carries a baseline
`classification` ("keep") and a `reason`; TASK-E-02/E-03 change the rows they act on.

Usage (credentials from the environment; never hard-coded):
  ERPNEXT_URL=http://localhost:8080 ERPNEXT_USER=Administrator ERPNEXT_PASSWORD=... \
    python3 scripts/gen_field_register.py
"""

import csv
import http.cookiejar
import json
import os
import sys
import urllib.parse
import urllib.request

BASE = os.environ.get("ERPNEXT_URL", "").rstrip("/")
USER = os.environ.get("ERPNEXT_USER", "")
PASSWORD = os.environ.get("ERPNEXT_PASSWORD", "")
if not BASE or not USER or not PASSWORD:
    sys.exit("Set ERPNEXT_URL, ERPNEXT_USER and ERPNEXT_PASSWORD")

DOCTYPES = [
    "Item",
    "Item Barcode",
    "Item Price",
    "UOM",
    "UOM Conversion Detail",
    "Customer",
    "Customer Credit Limit",
    "Supplier",
    "Price List",
    "Sales Invoice",
    "Sales Invoice Item",
    "Sales Order",
    "Sales Order Item",
    "Delivery Note",
    "Purchase Invoice",
    "Purchase Invoice Item",
    "Payment Entry",
    "Payment Terms Template",
    "Payment Terms Template Detail",
    "Mode of Payment",
    "Warehouse",
    "Stock Entry",
    "Stock Entry Detail",
    "POS Profile",
    "POS Payment Method",
    "Company",
    "Account",
    "Fiscal Year",
]

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

login = urllib.request.Request(
    BASE + "/api/method/login",
    data=urllib.parse.urlencode({"usr": USER, "pwd": PASSWORD}).encode(),
)
opener.open(login).read()


def get_json(path):
    with opener.open(BASE + path) as response:
        return json.loads(response.read())


rows = []
seen = set()
for doctype in DOCTYPES:
    meta = get_json("/api/resource/DocType/" + urllib.parse.quote(doctype))["data"]
    for field in meta.get("fields", []):
        key = (doctype, field.get("fieldname", ""))
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "doctype": doctype,
                "fieldname": field.get("fieldname", ""),
                "fieldtype": field.get("fieldtype", ""),
                "label": field.get("label", ""),
                "options": field.get("options", ""),
                "reqd": field.get("reqd", 0),
                "hidden": field.get("hidden", 0),
                "read_only": field.get("read_only", 0),
                "module": meta.get("module", ""),
                "source": "DocField",
                "classification": "keep",
                "reason": "baseline keep; E-02/E-03 change the rows they act on",
            }
        )

    filters = urllib.parse.quote(json.dumps([["dt", "=", doctype]]))
    custom = get_json(
        "/api/resource/" + urllib.parse.quote("Custom Field") + "?filters="
        + filters
        + "&fields="
        + urllib.parse.quote(
            json.dumps(
                [
                    "fieldname",
                    "fieldtype",
                    "label",
                    "options",
                    "reqd",
                    "hidden",
                    "read_only",
                    "module",
                ]
            )
        )
        + "&limit_page_length=0"
    )["data"]
    for field in custom:
        key = (doctype, field.get("fieldname", ""))
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "doctype": doctype,
                "fieldname": field.get("fieldname", ""),
                "fieldtype": field.get("fieldtype", ""),
                "label": field.get("label", ""),
                "options": field.get("options", ""),
                "reqd": field.get("reqd", 0),
                "hidden": field.get("hidden", 0),
                "read_only": field.get("read_only", 0),
                "module": field.get("module") or "",
                "source": "Custom Field",
                "classification": "keep",
                "reason": "baseline keep; E-02/E-03 change the rows they act on",
            }
        )

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "erp-field-register.csv")
with open(path, "w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print(f"{len(rows)} rows written to {path}")
