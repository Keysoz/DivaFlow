#!/usr/bin/env python3
"""Integration test for the Party Statement Script Report.

Creates a disposable customer with two invoices, three partial payments and one
advance, then checks the report totals against the General Ledger.

    ERPNEXT_URL=http://localhost:8080 \
    ERPNEXT_USER=Administrator ERPNEXT_PASSWORD=admin \
    python3 scripts/test_party_statement.py

The script needs the custom_reports app installed on the site. It removes the
documents it creates; if a hard failure leaves data behind, the names are
printed so they can be cleaned up manually.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import date, timedelta
from typing import Any, cast
from uuid import uuid4

import httpx

BASE = os.environ.get("ERPNEXT_URL", "").rstrip("/")
USER = os.environ.get("ERPNEXT_USER", "")
PASSWORD = os.environ.get("ERPNEXT_PASSWORD", "")
if not (BASE and USER and PASSWORD):
    sys.exit("Set ERPNEXT_URL, ERPNEXT_USER and ERPNEXT_PASSWORD")

KEEP_DATA = os.environ.get("KEEP_DATA") == "1"
REPORT_JSON = os.environ.get("PARTY_STATEMENT_JSON", "")

SUFFIX = uuid4().hex[:6].upper()
CUSTOMER = f"PS Customer {SUFFIX}"
TODAY = date.today()
DUE = TODAY + timedelta(days=30)

REPORT_NAME = "Party Statement"
PRINT_FORMAT = "Party Statement Print"

http = httpx.Client(base_url=BASE, timeout=120)
http.post("/api/method/login", data={"usr": USER, "pwd": PASSWORD}).raise_for_status()

failures = 0
created: list[tuple[str, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    global failures
    print(("OK   " if ok else "FAIL ") + label + (f" — {detail}" if detail else ""))
    failures += 0 if ok else 1


def get_list(
    doctype: str, filters: list[list[Any]], fields: list[str], limit: int = 0
) -> list[dict[str, Any]]:
    response = http.get(
        f"/api/resource/{doctype}",
        params={
            "filters": json.dumps(filters),
            "fields": json.dumps(fields),
            "limit_page_length": str(limit),
        },
    )
    response.raise_for_status()
    return cast(list[dict[str, Any]], response.json().get("data") or [])


def create(doctype: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = http.post(f"/api/resource/{doctype}", json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"{doctype} create failed: {response.status_code} {response.text[:500]}")
    doc = cast(dict[str, Any], response.json()["data"])
    created.append((doctype, doc["name"]))
    return doc


def fetch(doctype: str, name: str) -> dict[str, Any]:
    response = http.get(f"/api/resource/{doctype}/{name}")
    response.raise_for_status()
    return cast(dict[str, Any], response.json()["data"])


def submit(doctype: str, name: str) -> dict[str, Any]:
    doc = fetch(doctype, name)
    response = http.post("/api/method/frappe.client.submit", data={"doc": json.dumps(doc)})
    if response.status_code >= 400:
        raise RuntimeError(f"{doctype} submit failed: {response.status_code} {response.text[:500]}")
    return cast(dict[str, Any], response.json()["message"])


def cancel_and_delete(doctype: str, name: str) -> None:
    """Cancel and remove a test document, including its cancelled ledger rows.

    A cancelled voucher keeps its GL Entry rows (is_cancelled=1). Frappe's link
    check refuses to delete the voucher while they exist, so remove those
    cancelled rows first. They have no accounting effect.
    """
    http.post("/api/method/frappe.client.cancel", data={"doctype": doctype, "name": name})
    for ledger in ("GL Entry", "Payment Ledger Entry"):
        for row in get_list(
            ledger,
            [["voucher_type", "=", doctype], ["voucher_no", "=", name]],
            ["name"],
        ):
            http.delete(f"/api/resource/{ledger}/{row['name']}")
    response = http.delete(f"/api/resource/{doctype}/{name}")
    if response.status_code >= 400:
        print(f"note: left cancelled {doctype} {name} ({response.status_code})")


def first_company() -> dict[str, Any]:
    rows = get_list(
        "Company",
        [],
        [
            "name",
            "default_currency",
            "default_receivable_account",
            "default_income_account",
            "cost_center",
        ],
        limit=1,
    )
    if not rows:
        raise RuntimeError("No Company found on the site")
    return rows[0]


def first_leaf(doctype: str) -> str:
    rows = get_list(doctype, [["is_group", "=", 0]], ["name"], limit=1)
    if not rows:
        raise RuntimeError(f"No {doctype} found on the site")
    return cast(str, rows[0]["name"])


TEST_ITEM = "PS-TEST-SERVICE"


def service_item(currency: str) -> str:
    """A deterministic non-stock item priced at 1,200 per Dozen."""
    rows = get_list("Item", [["name", "=", TEST_ITEM]], ["name"])
    if not rows:
        create(
            "Item",
            {
                "item_code": TEST_ITEM,
                "item_name": "Party Statement test service",
                "item_group": first_leaf("Item Group"),
                "stock_uom": "Dozen",
                "is_stock_item": 0,
                "standard_rate": 1200,
            },
        )
    prices = get_list(
        "Item Price",
        [
            ["item_code", "=", TEST_ITEM],
            ["price_list", "=", "Standard Selling"],
            ["uom", "=", "Dozen"],
        ],
        ["name", "price_list_rate"],
    )
    if not prices:
        create(
            "Item Price",
            {
                "item_code": TEST_ITEM,
                "price_list": "Standard Selling",
                "price_list_rate": 1200,
                "uom": "Dozen",
                "currency": currency,
                "selling": 1,
            },
        )
    return TEST_ITEM


def sales_invoice(company: dict[str, Any], item: str, amount: float) -> str:
    payload = {
        "customer": CUSTOMER,
        "company": company["name"],
        "posting_date": TODAY.isoformat(),
        "due_date": DUE.isoformat(),
        "currency": company["default_currency"],
        "conversion_rate": 1,
        "selling_price_list": "Standard Selling",
        "price_list_currency": company["default_currency"],
        "plc_conversion_rate": 1,
        "items": [
            {
                "item_code": item,
                "qty": 1,
                "uom": "Dozen",
                "rate": amount,
                "income_account": company["default_income_account"],
                "cost_center": company["cost_center"],
            }
        ],
    }
    return cast(str, create("Sales Invoice", payload)["name"])


def payment_entry(
    company: dict[str, Any],
    amount: float,
    reference: str | None,
    cash_account: str,
) -> str:
    payload: dict[str, Any] = {
        "payment_type": "Receive",
        "party_type": "Customer",
        "party": CUSTOMER,
        "company": company["name"],
        "posting_date": TODAY.isoformat(),
        "paid_from": company["default_receivable_account"],
        "paid_to": cash_account,
        "paid_from_account_currency": company["default_currency"],
        "paid_to_account_currency": company["default_currency"],
        "paid_amount": amount,
        "received_amount": amount,
        "source_exchange_rate": 1,
        "target_exchange_rate": 1,
        "mode_of_payment": "Cash",
        "reference_no": f"PS-{SUFFIX}-{amount:g}",
        "reference_date": TODAY.isoformat(),
        "references": (
            [
                {
                    "reference_doctype": "Sales Invoice",
                    "reference_name": reference,
                    "allocated_amount": amount,
                }
            ]
            if reference
            else []
        ),
    }
    return cast(str, create("Payment Entry", payload)["name"])


def gl_balance(company: str, receivable_account: str) -> float:
    rows = get_list(
        "GL Entry",
        [
            ["company", "=", company],
            ["party_type", "=", "Customer"],
            ["party", "=", CUSTOMER],
            ["account", "=", receivable_account],
            ["is_cancelled", "=", 0],
        ],
        ["debit", "credit"],
    )
    return sum(float(row["debit"]) - float(row["credit"]) for row in rows)


def run_report(company: str, from_date: str) -> dict[str, Any]:
    response = http.post(
        "/api/method/frappe.desk.query_report.run",
        data={
            "report_name": REPORT_NAME,
            "filters": json.dumps(
                {
                    "company": company,
                    "party_type": "Customer",
                    "party": CUSTOMER,
                    "from_date": from_date,
                    "to_date": TODAY.isoformat(),
                    "show_cancelled": 0,
                }
            ),
        },
    )
    if response.status_code >= 400:
        raise RuntimeError(f"report failed: {response.status_code} {response.text[:800]}")
    return cast(dict[str, Any], response.json()["message"])


company = first_company()
company_name = cast(str, company["name"])
company_receivable = cast(str, company["default_receivable_account"])
item = service_item(cast(str, company["default_currency"]))
cash_rows = get_list(
    "Account",
    [["company", "=", company_name], ["account_type", "=", "Cash"], ["is_group", "=", 0]],
    ["name"],
    limit=1,
)
if not cash_rows:
    raise RuntimeError("No cash account found")
cash_account = cast(str, cash_rows[0]["name"])

invoices: list[str] = []
payments: list[str] = []

try:
    # --- Test data ---------------------------------------------------------
    create(
        "Customer",
        {
            "customer_name": CUSTOMER,
            "customer_group": first_leaf("Customer Group"),
            "territory": first_leaf("Territory"),
        },
    )

    invoices.append(sales_invoice(company, item, 1200))
    invoices.append(sales_invoice(company, item, 1200))
    for invoice in invoices:
        submit("Sales Invoice", invoice)

    payments.append(payment_entry(company, 400, invoices[0], cash_account))
    payments.append(payment_entry(company, 300, invoices[0], cash_account))
    payments.append(payment_entry(company, 200, invoices[1], cash_account))
    payments.append(payment_entry(company, 100, None, cash_account))  # advance
    for entry in payments:
        submit("Payment Entry", entry)

    # --- Run the report ----------------------------------------------------
    fiscal_start_response = http.get(
        "/api/method/custom_reports.custom_reports.report.party_statement."
        "party_statement.get_fiscal_year_start",
        params={"company": company_name},
    )
    fiscal_start_response.raise_for_status()
    from_date = cast(str, fiscal_start_response.json()["message"])

    message = run_report(company_name, from_date)
    rows = cast(list[dict[str, Any]], message.get("result") or [])
    summary = {row["label"]: float(row["value"]) for row in message.get("report_summary") or []}

    sections: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        sections.setdefault(row.get("section", ""), []).append(row)

    # --- Assertions --------------------------------------------------------
    check("report returns rows", bool(rows), f"{len(rows)} rows")
    check(
        "two invoices in the invoice section",
        len(sections.get("invoice", [])) == 2,
        str([r["document"] for r in sections.get("invoice", [])]),
    )
    check(
        "four payments in the payment section",
        len(sections.get("payment", [])) == 4,
        str([r["document"] for r in sections.get("payment", [])]),
    )
    check(
        "one advance in the advance section",
        len(sections.get("advance", [])) == 1,
        str([r["document"] for r in sections.get("advance", [])]),
    )

    by_document = {row["document"]: row for row in sections.get("invoice", [])}
    first = by_document[invoices[0]]
    second = by_document[invoices[1]]
    check(
        "first invoice paid 700 and outstanding 500",
        first["paid"] == 700 and first["outstanding"] == 500,
        f"paid={first['paid']} outstanding={first['outstanding']}",
    )
    check(
        "second invoice paid 200 and outstanding 1000",
        second["paid"] == 200 and second["outstanding"] == 1000,
        f"paid={second['paid']} outstanding={second['outstanding']}",
    )

    check("summary opening is 0", summary.get("Opening Balance") == 0, str(summary))
    check("summary invoiced is 2400", summary.get("Total Invoiced") == 2400, str(summary))
    check("summary paid is 1000", summary.get("Total Paid") == 1000, str(summary))
    check("summary closing is 1400", summary.get("Remaining Balance") == 1400, str(summary))
    check(
        "advance total is 100",
        float(rows[0].get("advances_total") or 0) == 100,
        str(rows[0].get("advances_total")),
    )

    gl = gl_balance(company_name, company_receivable)
    check("report closing matches the GL", abs(gl - 1400) < 0.01, f"GL={gl:.2f}")
    check(
        "report does not flag a mismatch",
        rows[0].get("mismatch") is False and not message.get("message"),
        str(message.get("message")),
    )

    # --- Print format ------------------------------------------------------
    print_response = http.post(
        "/api/method/frappe.desk.query_report.get_print_format_data",
        data={"print_format": PRINT_FORMAT},
    )
    check(
        "report print format is available",
        print_response.status_code == 200
        and "diva-ps" in print_response.text
        and "Account Statement" in print_response.text,
        f"HTTP {print_response.status_code}",
    )

    print("\nParty Statement report and print format verified.")
    if KEEP_DATA:
        if REPORT_JSON:
            with open(REPORT_JSON, "w", encoding="utf-8") as handle:
                json.dump(message, handle, indent=2)
        print(f"kept test data for {CUSTOMER}")
finally:
    if KEEP_DATA:
        print(f"KEEP_DATA=1: documents for {CUSTOMER} were left in place")
    else:
        # --- Cleanup: payments first, then invoices, then the customer ------
        for doctype, name in reversed(created):
            try:
                if doctype in ("Payment Entry", "Sales Invoice"):
                    cancel_and_delete(doctype, name)
                else:
                    http.delete(f"/api/resource/{doctype}/{name}")
            except Exception:
                traceback.print_exc()
                print(f"warning: could not clean up {doctype} {name}")

if failures:
    sys.exit(f"{failures} check(s) failed")
