#!/usr/bin/env python3
"""Seed a synthetic China import treated as an EGP supplier (TASK-E-08b, DEC-75).

Owner decision: no foreign currency and no exchange-rate handling. The Chinese
supplier is registered like an Egyptian supplier with EGP item prices; the flow
still uses Purchase Order, partial Purchase Receipts, a Landed Cost Voucher for
freight/customs, a Purchase Invoice and two instalment payments (40% then 60%).

Idempotent: every document carries the marker ``DIVA-CHINA-001`` where the
doctype has a remarks field, or a matching bill/reference. Re-running creates
only the missing steps. All data is synthetic; never run against production.

Prerequisites on the dev site: company "Diva Dev", item "BULK-ACC-01" (stock UOM
Nos, Dozen conversion 12), warehouse "Main Inventory - DD", accounts
"Diva Bank - DD", "Creditors - DD" and "Freight and Forwarding Charges - DD".

Credentials from the environment:
  ERPNEXT_URL=... ERPNEXT_USER=... ERPNEXT_PASSWORD=... python3 scripts/seed_china_import.py
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
SUPPLIER = "China Supplier 1"
SUPPLIER_GROUP = "China"
ITEM = "BULK-ACC-01"
WAREHOUSE = f"Main Inventory - {ABBR}"
BANK = f"Diva Bank - {ABBR}"
QTY_DOZEN = 10
RATE = Decimal("1200")
FREIGHT = Decimal("1200")
BILL = "DIVA-CHN-001"
PAYMENT_REF = "DIVA-CHN-001"
MARKER = "DIVA-CHINA-001"

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


def submit_doctype(doctype: str, name: str) -> dict[str, Any]:
    doc = fetch(doctype, name)
    response = http.post("/api/method/frappe.client.submit", data={"doc": json.dumps(doc)})
    response.raise_for_status()
    return cast(dict[str, Any], response.json()["message"])


def ensure_supplier() -> None:
    groups = get_list("Supplier Group", [["supplier_group_name", "=", SUPPLIER_GROUP]], ["name"])
    if not groups:
        create(
            "Supplier Group",
            {
                "supplier_group_name": SUPPLIER_GROUP,
                "parent_supplier_group": "All Supplier Groups",
                "is_group": 0,
            },
        )
    suppliers = get_list("Supplier", [["name", "=", SUPPLIER]], ["name"])
    if not suppliers:
        create(
            "Supplier",
            {
                "supplier_name": SUPPLIER,
                "supplier_group": SUPPLIER_GROUP,
                "country": "China",
                "default_currency": "EGP",
            },
        )


def ensure_purchase_order() -> dict[str, Any]:
    rows = get_list(
        "Purchase Order",
        [["supplier", "=", SUPPLIER], ["title", "=", MARKER], ["docstatus", "=", 1]],
        ["name"],
    )
    if rows:
        return fetch("Purchase Order", rows[0]["name"])
    order = create(
        "Purchase Order",
        {
            "supplier": SUPPLIER,
            "company": COMPANY,
            "transaction_date": "2026-10-28",
            "schedule_date": "2026-10-28",
            "currency": "EGP",
            "conversion_rate": 1,
            "title": MARKER,
            "items": [
                {
                    "item_code": ITEM,
                    "qty": QTY_DOZEN,
                    "uom": "Dozen",
                    "conversion_factor": 12,
                    "warehouse": WAREHOUSE,
                    "rate": float(RATE),
                    "schedule_date": "2026-10-28",
                }
            ],
        },
    )
    submit_doctype("Purchase Order", order["name"])
    return fetch("Purchase Order", order["name"])


def create_receipt(order: dict[str, Any], qty: int) -> str:
    item = order["items"][0]
    receipt = create(
        "Purchase Receipt",
        {
            "supplier": SUPPLIER,
            "company": COMPANY,
            "posting_date": "2026-10-28",
            "posting_time": "10:00:00",
            "currency": "EGP",
            "conversion_rate": 1,
            "remarks": MARKER,
            "items": [
                {
                    "item_code": ITEM,
                    "qty": qty,
                    "uom": "Dozen",
                    "conversion_factor": 12,
                    "warehouse": WAREHOUSE,
                    "rate": float(RATE),
                    "purchase_order": order["name"],
                    "purchase_order_item": item["name"],
                }
            ],
        },
    )
    submit_doctype("Purchase Receipt", receipt["name"])
    return str(receipt["name"])


def ensure_receipts(order: dict[str, Any]) -> list[str]:
    receipts = get_list(
        "Purchase Receipt",
        [["supplier", "=", SUPPLIER], ["docstatus", "=", 1], ["remarks", "=", MARKER]],
        ["name"],
    )
    names = [row["name"] for row in receipts]
    if len(names) >= 2:
        return names
    # Sum the marked receipts themselves; never assume PO received_qty UOM.
    received = sum(
        (
            Decimal(str(line.get("qty") or 0))
            for name in names
            for line in fetch("Purchase Receipt", name).get("items") or []
        ),
        Decimal("0"),
    )
    if received < 6:
        names.append(create_receipt(order, int(Decimal("6") - received)))
        received = Decimal("6")
    if received < QTY_DOZEN:
        names.append(create_receipt(order, int(QTY_DOZEN - received)))
    return names


def ensure_landed_cost(receipts: list[str]) -> str:
    wanted = set(receipts)
    for row in get_list("Landed Cost Voucher", [["docstatus", "=", 1]], ["name"]):
        lcv = fetch("Landed Cost Voucher", row["name"])
        linked = {str(line.get("receipt_document")) for line in lcv.get("purchase_receipts") or []}
        marker = any(
            "DIVA-CHINA" in str(tax.get("description", "")) for tax in lcv.get("taxes") or []
        )
        if wanted <= linked and marker:
            return str(lcv["name"])
    lcv = create(
        "Landed Cost Voucher",
        {
            "company": COMPANY,
            "posting_date": "2026-10-28",
            "distribute_charges_based_on": "Amount",
            "purchase_receipts": [
                {
                    "receipt_document_type": "Purchase Receipt",
                    "receipt_document": receipt,
                    "supplier": SUPPLIER,
                }
                for receipt in receipts
            ],
            "taxes": [
                {
                    "expense_account": f"Freight and Forwarding Charges - {ABBR}",
                    "description": "DIVA-CHINA freight and customs",
                    "amount": float(FREIGHT),
                }
            ],
        },
    )
    submit_doctype("Landed Cost Voucher", lcv["name"])
    return str(lcv["name"])


def ensure_invoice(order: dict[str, Any], receipts: list[str]) -> dict[str, Any]:
    rows = get_list(
        "Purchase Invoice",
        [["supplier", "=", SUPPLIER], ["bill_no", "=", BILL], ["docstatus", "=", 1]],
        ["name"],
    )
    if rows:
        return fetch("Purchase Invoice", rows[0]["name"])
    items: list[dict[str, Any]] = []
    for receipt in receipts:
        detail = fetch("Purchase Receipt", receipt)
        for row in detail["items"]:
            items.append(
                {
                    "item_code": ITEM,
                    "qty": row["qty"],
                    "uom": "Dozen",
                    "conversion_factor": 12,
                    "warehouse": WAREHOUSE,
                    "rate": float(RATE),
                    "purchase_receipt": receipt,
                    "pr_detail": row["name"],
                    "purchase_order": order["name"],
                    "po_detail": order["items"][0]["name"],
                }
            )
    invoice = create(
        "Purchase Invoice",
        {
            "supplier": SUPPLIER,
            "company": COMPANY,
            "posting_date": "2026-10-28",
            "bill_no": BILL,
            "bill_date": "2026-10-28",
            "currency": "EGP",
            "conversion_rate": 1,
            "update_stock": 0,
            "remarks": MARKER,
            "items": items,
        },
    )
    submit_doctype("Purchase Invoice", invoice["name"])
    return fetch("Purchase Invoice", invoice["name"])


def ensure_payments(invoice: dict[str, Any]) -> list[str]:
    rows = get_list(
        "Payment Entry",
        [
            ["party_type", "=", "Supplier"],
            ["party", "=", SUPPLIER],
            ["reference_no", "=", PAYMENT_REF],
            ["docstatus", "=", 1],
        ],
        ["name", "paid_amount"],
    )
    paid = sum((Decimal(str(row["paid_amount"])) for row in rows), Decimal("0"))
    outstanding = Decimal(str(invoice.get("outstanding_amount") or 0))
    created: list[str] = []
    # 40% first, then the remaining 60% (or whatever is still outstanding).
    for target in (Decimal("4800"), Decimal("12000")):
        if paid >= target or outstanding <= 0:
            continue
        amount = min(target - paid, outstanding)
        payment = create(
            "Payment Entry",
            {
                "payment_type": "Pay",
                "company": COMPANY,
                "posting_date": "2026-10-28",
                "paid_from": BANK,
                "paid_to": f"Creditors - {ABBR}",
                "party_type": "Supplier",
                "party": SUPPLIER,
                "paid_amount": float(amount),
                "received_amount": float(amount),
                "reference_no": PAYMENT_REF,
                "reference_date": "2026-10-28",
                "remarks": MARKER,
                "references": [
                    {
                        "reference_doctype": "Purchase Invoice",
                        "reference_name": invoice["name"],
                        "allocated_amount": float(amount),
                    }
                ],
            },
        )
        submit_doctype("Payment Entry", payment["name"])
        created.append(payment["name"])
        paid += amount
        outstanding -= amount
    return created


def supplier_gl_balance() -> Decimal:
    rows = get_list(
        "GL Entry",
        [
            ["party_type", "=", "Supplier"],
            ["party", "=", SUPPLIER],
            ["is_cancelled", "=", 0],
        ],
        ["debit", "credit"],
    )
    return sum(
        (Decimal(str(row["debit"])) - Decimal(str(row["credit"])) for row in rows),
        Decimal("0"),
    )


ensure_supplier()
order = ensure_purchase_order()
receipts = ensure_receipts(order)
landed = ensure_landed_cost(receipts)
invoice = ensure_invoice(order, receipts)
payments = ensure_payments(invoice)
invoice = fetch("Purchase Invoice", invoice["name"])
order = fetch("Purchase Order", order["name"])

stock_rows = get_list(
    "Stock Ledger Entry",
    [["voucher_no", "in", [*receipts, landed]], ["is_cancelled", "=", 0]],
    ["actual_qty", "stock_value_difference"],
)
stock_qty = sum((Decimal(str(row["actual_qty"])) for row in stock_rows), Decimal("0"))
stock_value = sum((Decimal(str(row["stock_value_difference"])) for row in stock_rows), Decimal("0"))
payment_rows = get_list(
    "Payment Entry",
    [["reference_no", "=", PAYMENT_REF], ["docstatus", "=", 1]],
    ["name", "paid_amount"],
)
paid_total = sum((Decimal(str(row["paid_amount"])) for row in payment_rows), Decimal("0"))
balance = supplier_gl_balance()

print("PO", order["name"], "received", order["per_received"], "billed", order["per_billed"])
print("receipts", receipts)
print("landed cost", landed, "freight", FREIGHT)
print(
    "invoice",
    invoice["name"],
    "total",
    invoice["grand_total"],
    "outstanding",
    invoice["outstanding_amount"],
)
print("payments", [row["name"] for row in payment_rows], "total", paid_total)
print("stock movement", stock_qty, "Nos; value", stock_value)
print("supplier GL balance", balance)

failed = False
checks = [
    (stock_qty == Decimal(QTY_DOZEN * 12), "10 Dozen received in stock"),
    (stock_value == (RATE * QTY_DOZEN) + FREIGHT, "stock value includes the landed cost"),
    (Decimal(str(order["per_received"])) == 100, "PO fully received"),
    (Decimal(str(order["per_billed"])) == 100, "PO fully billed"),
    (Decimal(str(invoice["outstanding_amount"])) == 0, "invoice fully paid"),
    (paid_total == RATE * QTY_DOZEN, "two instalments total the invoice"),
    (balance == 0, "supplier balance is zero"),
    (len(payment_rows) == 2, "two payment history rows"),
]
for ok, label in checks:
    print(("OK   " if ok else "FAIL ") + label)
    failed = failed or not ok
if failed:
    print("E-08b China import checks FAILED")
raise SystemExit(1 if failed else 0)
