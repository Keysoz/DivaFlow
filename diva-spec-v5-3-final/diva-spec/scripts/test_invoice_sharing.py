#!/usr/bin/env python3
"""Invoice sharing level 1 checks (E-18, DEC-97).

Builds the free `wa.me` link with a normalized Egyptian number and a ready
Arabic or English message for a Sales Invoice, Purchase Invoice and Payment
Entry, and checks the print format and the missing-phone error.

Usage:
  ERPNEXT_URL=http://localhost:8080 ERPNEXT_USER=Administrator \
  ERPNEXT_PASSWORD=admin python3 scripts/test_invoice_sharing.py
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
ITEM = "BULK-ACC-01"
STAMP = time.strftime("%H%M%S")
CUSTOMER = f"SHARE-CUST-{STAMP}"
SUPPLIER = f"SHARE-SUP-{STAMP}"
NO_PHONE = f"SHARE-NOPHONE-{STAMP}"
MOBILE = "01001234567"
EXPECTED = "201001234567"

failures = 0
created: list[tuple[str, str]] = []

http = httpx.Client(base_url=BASE, timeout=120)
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
    messages = payload.get("_server_messages") if isinstance(payload, dict) else None
    if messages:
        try:
            return " | ".join(json.loads(m).get("message", "") for m in json.loads(messages))[:400]
        except (ValueError, TypeError):
            return str(messages)[:400]
    return str(payload.get("exception") or payload)[:400]


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


def share(doctype: str, name: str, language: str = "ar") -> httpx.Response:
    return http.post(
        "/api/method/diva_guard.share.invoice_share",
        data={"doctype": doctype, "name": name, "language": language},
    )


def check_document(doctype: str, name: str, print_format: str, amount: float) -> None:
    response = share(doctype, name)
    if response.status_code >= 400:
        expect(f"{doctype}: share link is built", False, error_of(response))
        return
    data = response.json()["message"]
    expect(f"{doctype}: number is normalized", data.get("phone") == EXPECTED, data.get("phone"))
    expect(
        f"{doctype}: wa.me link is correct",
        str(data.get("wa_link", "")).startswith(f"https://wa.me/{EXPECTED}?text="),
        data.get("wa_link"),
    )
    expect(
        f"{doctype}: message has the document",
        name in str(data.get("message")),
        data.get("message"),
    )
    expect(
        f"{doctype}: message has the amount",
        f"{amount:,.2f}" in str(data.get("message")),
        data.get("message"),
    )
    expect(
        f"{doctype}: print format is set",
        data.get("print_format") == print_format,
        data.get("print_format"),
    )
    english = share(doctype, name, "en")
    expect(
        f"{doctype}: English message is available",
        english.status_code < 400 and "Hello" in str(english.json()["message"].get("message")),
        english.text[:200],
    )


def main() -> None:
    customer = create(
        "Customer", {"customer_name": CUSTOMER, "customer_type": "Individual", "mobile_no": MOBILE}
    )
    supplier = create(
        "Supplier", {"supplier_name": SUPPLIER, "supplier_type": "Individual", "mobile_no": MOBILE}
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
            "items": [{"item_code": ITEM, "qty": 2, "uom": "Dozen", "rate": 1200}],
        },
    )
    submit("Sales Invoice", sale)
    check_document("Sales Invoice", sale, "Diva Sales Invoice A4", 2400.0)

    purchase = create(
        "Purchase Invoice",
        {
            "supplier": supplier,
            "company": COMPANY,
            "currency": "EGP",
            "conversion_rate": 1,
            "update_stock": 0,
            "items": [{"item_code": ITEM, "qty": 2, "uom": "Dozen", "rate": 1000}],
        },
    )
    submit("Purchase Invoice", purchase)
    check_document("Purchase Invoice", purchase, "Diva Purchase Invoice A4", 2000.0)

    payment = http.post(
        "/api/method/diva_guard.desk_api.pay_invoice",
        data={"invoice_name": sale, "amount": 2400, "mode_of_payment": "Cash"},
    )
    if payment.status_code >= 400:
        expect("Payment Entry: pay creates a receipt", False, error_of(payment))
    else:
        entry = payment.json()["message"]["payment_entry"]
        created.append(("Payment Entry", entry))
        check_document("Payment Entry", entry, "Diva Payment Receipt", 2400.0)

    trunk = create(
        "Customer",
        {
            "customer_name": f"SHARE-TRUNK-{STAMP}",
            "customer_type": "Individual",
            "mobile_no": "+20-01018782245",
        },
    )
    trunk_invoice = create(
        "Sales Invoice",
        {
            "customer": trunk,
            "company": COMPANY,
            "currency": "EGP",
            "conversion_rate": 1,
            "update_stock": 0,
            "items": [{"item_code": ITEM, "qty": 2, "uom": "Dozen", "rate": 1200}],
        },
    )
    trunk_share = share("Sales Invoice", trunk_invoice)
    expect(
        "a +20 number with a trunk 0 is normalized",
        trunk_share.status_code < 400
        and trunk_share.json()["message"].get("phone") == "201018782245",
        trunk_share.text[:200],
    )

    no_phone = create("Customer", {"customer_name": NO_PHONE, "customer_type": "Individual"})
    draft = create(
        "Sales Invoice",
        {
            "customer": no_phone,
            "company": COMPANY,
            "currency": "EGP",
            "conversion_rate": 1,
            "update_stock": 0,
            "items": [{"item_code": ITEM, "qty": 2, "uom": "Dozen", "rate": 1200}],
        },
    )
    missing = share("Sales Invoice", draft)
    expect("a party without a phone is refused", missing.status_code >= 400, error_of(missing))
    expect(
        "the error explains how to fix it",
        "phone" in error_of(missing).lower() or "هاتف" in error_of(missing),
        error_of(missing),
    )

    print(
        "\n1. Print the Diva format from the browser print preview "
        "(server-side pdfkit is unavailable on the dev image)."
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
    print(f"\n{'FAILURES: ' + str(failures) if failures else 'all invoice sharing checks passed'}")
    sys.exit(1 if failures else 0)
