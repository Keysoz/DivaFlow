#!/usr/bin/env python3
"""Statement sharing checks (E-18, DEC-97).

The Party Statement report shares a customer or supplier statement through the
free `wa.me` link with a ready Arabic or English message. The message names the
party and the period only; the amounts stay in the printed statement.

Usage:
  ERPNEXT_URL=http://localhost:8080 ERPNEXT_USER=Administrator \
  ERPNEXT_PASSWORD=admin python3 scripts/test_statement_sharing.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

import httpx

BASE = os.environ.get("ERPNEXT_URL", "").rstrip("/")
USER = os.environ.get("ERPNEXT_USER", "")
PASSWORD = os.environ.get("ERPNEXT_PASSWORD", "")
if not (BASE and USER and PASSWORD):
    sys.exit("Set ERPNEXT_URL, ERPNEXT_USER and ERPNEXT_PASSWORD")

COMPANY = "Diva Dev"
STAMP = time.strftime("%H%M%S")
MOBILE = "01001234567"
EXPECTED = "201001234567"
FROM_DATE = "2026-01-01"
TO_DATE = "2026-10-31"

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


def share(**payload: Any) -> httpx.Response:
    return http.post("/api/method/diva_guard.share.statement_share", data=payload)


def check_statement(party_type: str, party: str) -> None:
    response = share(
        party_type=party_type,
        party=party,
        from_date=FROM_DATE,
        to_date=TO_DATE,
        company=COMPANY,
    )
    if response.status_code >= 400:
        expect(f"{party_type} statement: link is built", False, error_of(response))
        return
    data = response.json()["message"]
    expect(
        f"{party_type} statement: number is normalized",
        data.get("phone") == EXPECTED,
        data.get("phone"),
    )
    expect(
        f"{party_type} statement: wa.me link is correct",
        str(data.get("wa_link", "")).startswith(f"https://wa.me/{EXPECTED}?text="),
        data.get("wa_link"),
    )
    expect(
        f"{party_type} statement: message names the party",
        party in str(data.get("message")),
        data.get("message"),
    )
    expect(
        f"{party_type} statement: message has the period",
        "01-01-2026" in str(data.get("message")) and "31-10-2026" in str(data.get("message")),
        data.get("message"),
    )
    expect(
        f"{party_type} statement: message has the company",
        "Diva Dev" in str(data.get("message")),
        data.get("message"),
    )
    expect(
        f"{party_type} statement: print format is set",
        data.get("print_format") == "Party Statement Print",
        data.get("print_format"),
    )
    english = share(
        party_type=party_type,
        party=party,
        from_date=FROM_DATE,
        to_date=TO_DATE,
        company=COMPANY,
        language="en",
    )
    expect(
        f"{party_type} statement: English message is available",
        english.status_code < 400
        and "account statement" in str(english.json()["message"].get("message")),
        english.text[:200],
    )


def main() -> None:
    customer = create(
        "Customer",
        {"customer_name": f"STMT-CUST-{STAMP}", "customer_type": "Individual", "mobile_no": MOBILE},
    )
    supplier = create(
        "Supplier",
        {"supplier_name": f"STMT-SUP-{STAMP}", "supplier_type": "Individual", "mobile_no": MOBILE},
    )
    check_statement("Customer", customer)
    check_statement("Supplier", supplier)

    no_phone = create(
        "Customer", {"customer_name": f"STMT-NOPHONE-{STAMP}", "customer_type": "Individual"}
    )
    missing = share(
        party_type="Customer",
        party=no_phone,
        from_date=FROM_DATE,
        to_date=TO_DATE,
        company=COMPANY,
    )
    expect("a party without a phone is refused", missing.status_code >= 400, error_of(missing))
    expect(
        "the error explains how to fix it",
        "phone" in error_of(missing).lower() or "هاتف" in error_of(missing),
        error_of(missing),
    )

    invalid = share(
        party_type="Employee",
        party=customer,
        from_date=FROM_DATE,
        to_date=TO_DATE,
        company=COMPANY,
    )
    expect("an unsupported party type is refused", invalid.status_code >= 400, error_of(invalid))

    no_period = share(
        party_type="Customer", party=customer, from_date="", to_date="", company=COMPANY
    )
    expect("a missing period is refused", no_period.status_code >= 400, error_of(no_period))


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
    print(
        f"\n{'FAILURES: ' + str(failures) if failures else 'all statement sharing checks passed'}"
    )
    sys.exit(1 if failures else 0)
