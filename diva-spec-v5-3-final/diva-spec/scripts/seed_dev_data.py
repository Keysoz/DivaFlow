#!/usr/bin/env python3
"""Seed the disposable dev ERPNext with synthetic data (E-06/E-07/E-09).

Idempotent: existing warehouses/items/modes are skipped. Credentials from env:
  ERPNEXT_URL=... ERPNEXT_USER=... ERPNEXT_PASSWORD=... python3 scripts/seed_dev_data.py

Never run against production. All data is synthetic.
"""

import json
import os
import sys

import httpx

BASE = os.environ.get("ERPNEXT_URL", "").rstrip("/")
USER = os.environ.get("ERPNEXT_USER", "")
PASSWORD = os.environ.get("ERPNEXT_PASSWORD", "")
if not (BASE and USER and PASSWORD):
    sys.exit("Set ERPNEXT_URL, ERPNEXT_USER and ERPNEXT_PASSWORD")

http = httpx.Client(base_url=BASE, timeout=30)
http.post("/api/method/login", data={"usr": USER, "pwd": PASSWORD}).raise_for_status()

COMPANY = "Diva Dev"
ABBR = "DD"


def ean13(base12: str) -> str:
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(base12))
    return base12 + str((10 - total % 10) % 10)


def ensure_warehouse(name: str) -> str:
    full = f"{name} - {ABBR}"
    if http.get(f"/api/resource/Warehouse/{full}").status_code == 200:
        return full
    payload = {
        "warehouse_name": name,
        "company": COMPANY,
        "parent_warehouse": f"All Warehouses - {ABBR}",
    }
    response = http.post("/api/resource/Warehouse", json=payload)
    response.raise_for_status()
    return response.json()["data"]["name"]


def ensure_item(index: int, group: str) -> str:
    code = f"BULK-{group[:3].upper()}-{index:02d}"
    if http.get(f"/api/resource/Item/{code}").status_code == 200:
        return code
    group_code = 0 if group == "Accessories" else 1
    dozen = ean13(f"210{group_code}{index:04d}0001")
    piece = ean13(f"210{group_code}{index:04d}0002")
    payload = {
        "item_code": code,
        "item_name": f"Bulk {group} {index:02d}",
        "item_group": group,
        "stock_uom": "Nos",
        "is_stock_item": 1,
        "include_item_in_manufacturing": 0,
        "uoms": [{"uom": "Dozen", "conversion_factor": 12}],
        "barcodes": [
            {"barcode": dozen, "barcode_type": "EAN", "uom": "Dozen"},
            {"barcode": piece, "barcode_type": "EAN", "uom": "Nos"},
        ],
    }
    response = http.post("/api/resource/Item", json=payload)
    response.raise_for_status()
    http.post(
        "/api/resource/Item Price",
        json={
            "item_code": code,
            "price_list": "Standard Selling",
            "uom": "Dozen",
            "price_list_rate": 1200 + index * 24,
            "selling": 1,
        },
    ).raise_for_status()
    return code


def submit(doctype: str, payload: dict) -> dict:
    created = http.post(f"/api/resource/{doctype}", json=payload)
    created.raise_for_status()
    doc = created.json()["data"]
    submitted = http.post("/api/method/frappe.client.submit", data={"doc": json.dumps(doc)})
    submitted.raise_for_status()
    return submitted.json()["message"]


# --- Warehouses (DEC-49) ---
for name in ["Main Inventory", "Shop", "Gallery", "Returns and Defects"]:
    ensure_warehouse(name)
print("warehouses ready")

# --- Items with Dozen + piece barcodes and per-Dozen prices ---
items = [ensure_item(i, "Accessories") for i in range(1, 7)] + [
    ensure_item(i, "Cosmetics") for i in range(1, 7)
]
print("items ready:", len(items))

# --- Opening stock (Stock Reconciliation, 120 Nos per item in Main Inventory) ---
first = items[0]
bin_url = f'/api/resource/Bin?filters=[["item_code","=","{first}"]]&fields=["actual_qty"]'
bin_rows = http.get(bin_url).json().get("data") or []
if not bin_rows or float(bin_rows[0]["actual_qty"]) < 120:
    submit(
        "Stock Reconciliation",
        {
            "company": COMPANY,
            "purpose": "Opening Stock",
            "posting_date": "2026-10-28",
            "posting_time": "09:00:00",
            "expense_account": f"Temporary Opening - {ABBR}",
            "cost_center": f"Main - {ABBR}",
            "items": [
                {
                    "item_code": code,
                    "warehouse": f"Main Inventory - {ABBR}",
                    "qty": 120,
                    "valuation_rate": 100,
                }
                for code in items
            ],
        },
    )
    print("opening stock posted")

# --- Six payment modes (E-09; one account per mode, OPEN-10) ---
bank = f"Diva Bank - {ABBR}"
if http.get(f"/api/resource/Account/{bank}").status_code != 200:
    http.post(
        "/api/resource/Account",
        json={
            "account_name": "Diva Bank",
            "parent_account": f"Bank Accounts - {ABBR}",
            "company": COMPANY,
            "account_type": "Bank",
            "is_group": 0,
        },
    ).raise_for_status()
    print("bank ledger account created")

modes = {
    "Cash": ("Cash", f"Cash - {ABBR}"),
    "Bank Transfer": ("Bank", bank),
    "Vodafone Cash": ("Bank", bank),
    "InstaPay": ("Bank", bank),
    "ECash": ("Bank", bank),
    "WePay": ("Bank", bank),
}
for mode, (kind, account) in modes.items():
    if http.get(f"/api/resource/Mode of Payment/{mode}").status_code == 200:
        continue
    payload = {
        "mode_of_payment": mode,
        "type": kind,
        "enabled": 1,
        "accounts": [{"company": COMPANY, "default_account": account}],
    }
    response = http.post("/api/resource/Mode of Payment", json=payload)
    if response.status_code >= 400:
        print("mode failed:", mode, response.status_code, response.text[:160])
    else:
        print("mode created:", mode)

# --- E-08 purchasing: suppliers + a Purchase Invoice with Update Stock ---
for name in ["Bulk Supplier 1", "Bulk Supplier 2"]:
    if http.get(f"/api/resource/Supplier/{name}").status_code != 200:
        http.post(
            "/api/resource/Supplier",
            json={"supplier_name": name, "supplier_group": "Local", "country": "Egypt"},
        ).raise_for_status()
print("suppliers ready")

existing_pi = (
    http.get(
        '/api/resource/Purchase Invoice?filters=[["bill_no","=","BULK-PI-01"]]&fields=["name"]'
    )
    .json()
    .get("data")
    or []
)
if not existing_pi:
    submit(
        "Purchase Invoice",
        {
            "supplier": "Bulk Supplier 1",
            "company": COMPANY,
            "currency": "EGP",
            "conversion_rate": 1,
            "update_stock": 1,
            "bill_no": "BULK-PI-01",
            "bill_date": "2026-10-28",
            "items": [
                {
                    "item_code": "BULK-ACC-01",
                    "qty": 5,
                    "uom": "Dozen",
                    "warehouse": f"Main Inventory - {ABBR}",
                    "rate": 1000,
                },
                {
                    "item_code": "BULK-COS-01",
                    "qty": 5,
                    "uom": "Dozen",
                    "warehouse": f"Main Inventory - {ABBR}",
                    "rate": 1000,
                },
            ],
        },
    )
    print("purchase invoice posted")

# --- E-09 sales: customers + a paid POS invoice + a credit invoice ---
for i in range(1, 6):
    name = f"Bulk Customer {i:02d}"
    if http.get(f"/api/resource/Customer/{name}").status_code != 200:
        http.post(
            "/api/resource/Customer",
            json={
                "customer_name": name,
                "customer_group": "Commercial",
                "territory": "Egypt",
                "credit_limits": [{"company": COMPANY, "credit_limit": 20000}],
            },
        ).raise_for_status()
print("customers ready")

existing_si = (
    http.get(
        '/api/resource/Sales Invoice?filters=[["remarks","=","BULK-SEED-POS"]]&fields=["name"]'
    )
    .json()
    .get("data")
    or []
)
if not existing_si:
    submit(
        "Sales Invoice",
        {
            "is_pos": 1,
            "pos_profile": "P003 POS",
            "customer": "Bulk Customer 01",
            "company": COMPANY,
            "currency": "EGP",
            "conversion_rate": 1,
            "update_stock": 1,
            "selling_price_list": "Standard Selling",
            "price_list_currency": "EGP",
            "plc_conversion_rate": 1,
            "remarks": "BULK-SEED-POS",
            "items": [
                {
                    "item_code": "BULK-ACC-01",
                    "qty": 1,
                    "uom": "Dozen",
                    "warehouse": f"Main Inventory - {ABBR}",
                    "rate": 1224,
                }
            ],
            "payments": [{"mode_of_payment": "Cash", "amount": 1224}],
        },
    )
    print("paid POS invoice posted")

existing_credit = (
    http.get(
        '/api/resource/Sales Invoice?filters=[["remarks","=","BULK-SEED-CREDIT"]]&fields=["name"]'
    )
    .json()
    .get("data")
    or []
)
if not existing_credit:
    submit(
        "Sales Invoice",
        {
            "customer": "Bulk Customer 02",
            "company": COMPANY,
            "currency": "EGP",
            "conversion_rate": 1,
            "update_stock": 1,
            "selling_price_list": "Standard Selling",
            "price_list_currency": "EGP",
            "plc_conversion_rate": 1,
            "remarks": "BULK-SEED-CREDIT",
            "items": [
                {
                    "item_code": "BULK-COS-01",
                    "qty": 2,
                    "uom": "Dozen",
                    "warehouse": f"Main Inventory - {ABBR}",
                    "rate": 1248,
                }
            ],
        },
    )
    print("credit invoice posted")

# --- Verify E-06/E-08/E-09 ---
barcode_names = (
    http.get('/api/resource/Item Barcode?filters=[["parent","=","BULK-ACC-01"]]&fields=["name"]')
    .json()
    .get("data")
    or []
)
dozen_barcode = ""
if barcode_names:
    row = http.get(f"/api/resource/Item Barcode/{barcode_names[0]['name']}").json()["data"]
    dozen_barcode = str(row["barcode"])
barcode_rows = (
    http.get(
        f'/api/resource/Item Barcode?filters=[["barcode","=","{dozen_barcode}"]]&fields=["name"]'
    )
    .json()
    .get("data")
    or []
)
print("dozen barcode resolves:", bool(barcode_rows), dozen_barcode)
print(
    "bin BULK-ACC-01:",
    http.get(
        '/api/resource/Bin?filters=[["item_code","=","BULK-ACC-01"]]'
        '&fields=["actual_qty","warehouse"]'
    )
    .json()
    .get("data"),
)
print(
    "credit outstanding:",
    http.get(
        '/api/resource/Sales Invoice?filters=[["remarks","=","BULK-SEED-CREDIT"]]'
        '&fields=["grand_total","outstanding_amount"]'
    )
    .json()
    .get("data"),
)

# --- Verify ---
print(
    "warehouses:",
    http.get('/api/resource/Warehouse?fields=["name"]&limit_page_length=50').json()["data"],
)
print(
    "items:",
    len(
        http.get(
            '/api/resource/Item?filters=[["item_code","like","BULK-%"]]&fields=["name"]&limit_page_length=0'
        ).json()["data"]
    ),
)
print(
    "modes:",
    [
        m["name"]
        for m in http.get(
            '/api/resource/Mode of Payment?fields=["name"]&limit_page_length=50'
        ).json()["data"]
    ],
)
