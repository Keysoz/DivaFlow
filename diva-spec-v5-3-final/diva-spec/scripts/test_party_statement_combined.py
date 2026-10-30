#!/usr/bin/env python3
"""Combined Customer/Supplier Party Statement checks (DEC-91).

A person who is both a customer and a supplier is two ERPNext records with the
same name. The Party Statement now merges both ledgers into one net statement.
This script creates such a pair with one sale, one purchase and two payments,
runs the report with and without the merge, and checks the totals against the
ledger.

Usage:
  ERPNEXT_URL=http://localhost:8080 ERPNEXT_USER=Administrator \
  ERPNEXT_PASSWORD=admin python3 scripts/test_party_statement_combined.py
"""

from __future__ import annotations

import json
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
ITEM = "RD-852"
STAMP = time.strftime("%H%M%S")
PARTY = f"DIVA-BOTH-{STAMP}"
from_date = time.strftime("%Y-01-01")
to_date = time.strftime("%Y-12-31")

failures = 0
created: list[tuple[str, str]] = []

http = httpx.Client(base_url=BASE, timeout=120, headers={"Accept-Language": "en"})
http.post("/api/method/login", data={"usr": USER, "pwd": PASSWORD}).raise_for_status()


def expect(label: str, condition: Any, detail: Any = "") -> bool:
    global failures
    ok = bool(condition)
    print(("PASS " if ok else "FAIL ") + label + ("" if ok else f"  -> {detail}"))
    if not ok:
        failures += 1
    return ok


def error_of(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:400]
    if isinstance(payload, dict):
        messages = payload.get("_server_messages")
        if messages:
            try:
                return " | ".join(json.loads(m).get("message", "") for m in json.loads(messages))[
                    :400
                ]
            except (ValueError, TypeError):
                return str(messages)[:400]
        return str(payload.get("exception") or payload)[:400]
    return str(payload)[:400]


def create(doctype: str, payload: dict[str, Any]) -> str:
    response = http.post(f"/api/resource/{doctype}", json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"create {doctype}: {error_of(response)}")
    name = str(response.json()["data"]["name"])
    created.append((doctype, name))
    return name


def resource(doctype: str, name: str) -> dict[str, Any]:
    response = http.get(f"/api/resource/{doctype}/{name}")
    response.raise_for_status()
    return cast(dict[str, Any], response.json()["data"])


def submit(doctype: str, name: str) -> None:
    doc = resource(doctype, name)
    response = http.post("/api/method/frappe.client.submit", data={"doc": json.dumps(doc)})
    if response.status_code >= 400:
        raise RuntimeError(f"submit {doctype} {name}: {error_of(response)}")


def run_report(combine: int) -> dict[str, Any]:
    filters = {
        "company": COMPANY,
        "party_type": "Customer",
        "party": PARTY,
        "from_date": from_date,
        "to_date": to_date,
        "combine": combine,
    }
    response = http.post(
        "/api/method/frappe.desk.query_report.run",
        data={"report_name": "Party Statement", "filters": json.dumps(filters)},
    )
    if response.status_code >= 400:
        raise RuntimeError(f"report: {error_of(response)}")
    return cast(dict[str, Any], response.json()["message"])


def labels(message: dict[str, Any]) -> list[str]:
    return [str(row.get("type_label") or "") for row in message["result"]]


def rows_of(message: dict[str, Any], section: str) -> list[dict[str, Any]]:
    return [row for row in message["result"] if row.get("section") == section]


def main() -> None:
    print(f"Combined statement for {PARTY}")
    customer = create("Customer", {"customer_name": PARTY, "customer_type": "Individual"})
    supplier = create("Supplier", {"supplier_name": PARTY, "supplier_type": "Individual"})
    expect(
        "Customer and Supplier share the same name",
        customer == PARTY and supplier == PARTY,
        (customer, supplier),
    )

    sale = create(
        "Sales Invoice",
        {
            "customer": customer,
            "company": COMPANY,
            "currency": "EGP",
            "conversion_rate": 1,
            "update_stock": 0,
            "selling_price_list": "Standard Selling",
            "price_list_currency": "EGP",
            "plc_conversion_rate": 1,
            "items": [
                {"item_code": ITEM, "qty": 1, "uom": "Dozen", "conversion_factor": 12, "rate": 96}
            ],
        },
    )
    submit("Sales Invoice", sale)
    purchase = create(
        "Purchase Invoice",
        {
            "supplier": supplier,
            "company": COMPANY,
            "currency": "EGP",
            "conversion_rate": 1,
            "update_stock": 0,
            "items": [
                {"item_code": ITEM, "qty": 2, "uom": "Dozen", "conversion_factor": 12, "rate": 80}
            ],
        },
    )
    submit("Purchase Invoice", purchase)

    receive = create(
        "Payment Entry",
        {
            "payment_type": "Receive",
            "party_type": "Customer",
            "party": customer,
            "company": COMPANY,
            "paid_from": "Debtors - DD",
            "paid_to": "Cash - DD",
            "paid_from_account_currency": "EGP",
            "paid_to_account_currency": "EGP",
            "paid_amount": 500,
            "received_amount": 500,
            "source_exchange_rate": 1,
            "target_exchange_rate": 1,
            "references": [
                {
                    "reference_doctype": "Sales Invoice",
                    "reference_name": sale,
                    "allocated_amount": 96,
                }
            ],
        },
    )
    submit("Payment Entry", receive)
    pay = create(
        "Payment Entry",
        {
            "payment_type": "Pay",
            "party_type": "Supplier",
            "party": supplier,
            "company": COMPANY,
            "paid_from": "Cash - DD",
            "paid_to": "Creditors - DD",
            "paid_from_account_currency": "EGP",
            "paid_to_account_currency": "EGP",
            "paid_amount": 600,
            "received_amount": 600,
            "source_exchange_rate": 1,
            "target_exchange_rate": 1,
            "references": [
                {
                    "reference_doctype": "Purchase Invoice",
                    "reference_name": purchase,
                    "allocated_amount": 160,
                }
            ],
        },
    )
    submit("Payment Entry", pay)

    combined = run_report(1)
    rows = combined["result"]
    meta = rows[0] if rows else {}
    expect("the report merges both ledgers", bool(meta.get("combined")), meta.get("combined"))
    expect(
        "the party label is the combined label",
        bool(meta.get("party_label")),
        meta.get("party_label"),
    )
    expect(
        "the counterpart is the Supplier record",
        meta.get("counterparty_type") == "Supplier",
        meta.get("counterparty_type"),
    )
    sides = {row.get("party_side") for row in rows if row.get("party_side")}
    expect("both sides are present", sides == {"Customer", "Supplier"}, sides)
    invoice_sides = {row.get("party_side") for row in rows_of(combined, "invoice")}
    expect(
        "sales and purchases are both shown",
        invoice_sides == {"Customer", "Supplier"},
        invoice_sides,
    )
    payment_dirs = {row.get("direction_code") for row in rows_of(combined, "payment")}
    expect("payments in and out are both shown", payment_dirs == {"in", "out"}, payment_dirs)
    expect(
        "sales total is the customer invoice",
        abs(float(meta.get("sales_total") or 0) - 96.0) < 0.01,
        meta.get("sales_total"),
    )
    expect(
        "purchases total is the supplier invoice",
        abs(float(meta.get("purchases_total") or 0) - 160.0) < 0.01,
        meta.get("purchases_total"),
    )
    expect(
        "paid in is the customer receipt",
        abs(float(meta.get("paid_in_total") or 0) - 500.0) < 0.01,
        meta.get("paid_in_total"),
    )
    expect(
        "paid out is the supplier payment",
        abs(float(meta.get("paid_out_total") or 0) - 600.0) < 0.01,
        meta.get("paid_out_total"),
    )
    # (96 - 500) - (160 - 600) = 36 receivable
    expect(
        "net balance nets the two sides",
        abs(float(meta.get("closing_balance") or 0) - 36.0) < 0.01,
        meta.get("closing_balance"),
    )
    expect(
        "net balance matches the GL",
        abs(float(meta.get("closing_balance") or 0) - float(meta.get("gl_closing_balance") or 0))
        < 0.01,
        meta.get("gl_closing_balance"),
    )
    expect(
        "net receivable is reported",
        abs(float(meta.get("net_receivable") or 0) - 36.0) < 0.01,
        meta.get("net_receivable"),
    )
    expect(
        "no payable is reported",
        abs(float(meta.get("net_payable") or 0)) < 0.01,
        meta.get("net_payable"),
    )

    separated = run_report(0)
    separated_meta = separated["result"][0] if separated["result"] else {}
    expect(
        "without the merge only the customer side is shown",
        not separated_meta.get("combined"),
        separated_meta.get("combined"),
    )
    expect(
        "without the merge there is no Purchase row",
        "Purchase" not in labels(separated),
        labels(separated),
    )
    expect(
        "without the merge the customer balance is the advance",
        abs(float(separated_meta.get("closing_balance") or 0) + 404.0) < 0.01,
        separated_meta.get("closing_balance"),
    )

    print_format = http.post(
        "/api/method/frappe.desk.query_report.get_print_format_data",
        data={"print_format": "Party Statement"},
    )
    expect(
        "the Party Statement print format is registered",
        print_format.status_code < 400,
        print_format.text[:200],
    )
    if print_format.status_code < 400:
        html = print_format.json()["message"]["html"]
        expect(
            "the print format knows the combined layout",
            "meta.combined" in html and "Net payable to this party" in html,
            len(html),
        )


def cleanup() -> None:
    for doctype, name in reversed(created):
        try:
            doc = http.get(f"/api/resource/{doctype}/{name}")
            if doc.status_code == 200 and doc.json()["data"].get("docstatus") == 1:
                http.post(
                    "/api/method/frappe.client.cancel", data={"doctype": doctype, "name": name}
                )
            http.delete(f"/api/resource/{doctype}/{name}")
        except Exception as error:  # noqa: BLE001 - cleanup must never hide the result
            print(f"cleanup skipped for {doctype} {name}: {error}")


if __name__ == "__main__":
    try:
        main()
    finally:
        cleanup()
    print(
        f"\n{'FAILURES: ' + str(failures) if failures else 'all combined statement checks passed'}"
    )
    sys.exit(1 if failures else 0)
