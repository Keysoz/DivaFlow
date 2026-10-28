#!/usr/bin/env python3
"""Seed test staff users and verify the permission baseline (TASK-E-16).

Owner: System Manager. Manager: sales/purchase/stock managers, accounts access
and price-list edit. Cashier: Sales User + Stock User + the vendor's
POSNext Cashier role (required by POS Next, DEC-70), with price lists, Stock
Reconciliation and Journal Entry restricted.

Credentials and the test password come from the environment; never commit them:
  ERPNEXT_URL=... ERPNEXT_USER=... ERPNEXT_PASSWORD=... DIVA_TEST_PASSWORD=... \
    python3 scripts/seed_dev_users.py

Prerequisites on the dev site: company "Diva Dev", customer "Bulk Customer 01",
item "BULK-ACC-01" with a Dozen price, and the POSNext Cashier role (installed
with POS Next). All data is synthetic; never run against production.
"""

import json
import os
import uuid
from typing import Any

import httpx

BASE = os.environ.get("ERPNEXT_URL", "").rstrip("/")
ADMIN_USER = os.environ.get("ERPNEXT_USER", "")
ADMIN_PASSWORD = os.environ.get("ERPNEXT_PASSWORD", "")
TEST_PASSWORD = os.environ.get("DIVA_TEST_PASSWORD", "")

COMPANY = "Diva Dev"
TEST_CUSTOMER = "Bulk Customer 01"
TEST_ITEM = "BULK-ACC-01"
PROBE_REMARK = "E-16 permission probe"

USERS = {
    "manager@diva.test": {
        "first_name": "Diva Manager",
        "roles": [
            "Sales Manager",
            "Sales Master Manager",
            "Purchase Manager",
            "Stock Manager",
            "Accounts User",
        ],
    },
    "cashier@diva.test": {
        "first_name": "Diva Cashier",
        "roles": ["Sales User", "Stock User", "POSNext Cashier"],
    },
}


def ensure_user(admin: httpx.Client, email: str, spec: dict[str, Any]) -> None:
    roles = [str(role) for role in spec["roles"]]
    existing = admin.get(f"/api/resource/User/{email}")
    if existing.status_code == 200:
        current = {row["role"] for row in existing.json()["data"].get("roles", [])}
        missing = [role for role in roles if role not in current]
        if missing:
            admin.put(
                f"/api/resource/User/{email}",
                json={"roles": [{"role": role} for role in sorted(current | set(missing))]},
            ).raise_for_status()
            print("roles added:", email, missing)
        return
    response = admin.post(
        "/api/resource/User",
        json={
            "email": email,
            "first_name": spec["first_name"],
            "send_welcome_email": 0,
            "user_type": "System User",
            "new_password": TEST_PASSWORD,
            "roles": [{"role": role} for role in roles],
        },
    )
    response.raise_for_status()
    print("user created:", email)


def client_for(email: str) -> httpx.Client:
    client = httpx.Client(base_url=BASE, timeout=30)
    response = client.post("/api/method/login", data={"usr": email, "pwd": TEST_PASSWORD})
    response.raise_for_status()
    return client


def can_list(client: httpx.Client, doctype: str) -> bool:
    return client.get(f"/api/resource/{doctype}?limit_page_length=1").status_code == 200


def can_write_price_list(client: httpx.Client) -> bool:
    # No-op write (enabled is already 1); only the permission decision matters.
    response = client.put(
        "/api/resource/Price List/Standard Selling",
        json={"enabled": 1},
    )
    return response.status_code == 200


def can_create_user(admin: httpx.Client, client: httpx.Client) -> bool:
    """Try to create a throwaway user; delete it with the admin if allowed."""
    probe = f"permission-probe-{uuid.uuid4().hex[:8]}@diva.test"
    response = client.post(
        "/api/resource/User",
        json={"email": probe, "first_name": "Permission Probe"},
    )
    if response.status_code != 200:
        return False
    admin.delete(f"/api/resource/User/{probe}")
    return True


def can_create_invoice(client: httpx.Client) -> bool:
    """Create a draft invoice as the user; admin cleanup runs in main()."""
    payload = {
        "customer": TEST_CUSTOMER,
        "company": COMPANY,
        "currency": "EGP",
        "conversion_rate": 1,
        "selling_price_list": "Standard Selling",
        "price_list_currency": "EGP",
        "plc_conversion_rate": 1,
        "remarks": PROBE_REMARK,
        "items": [
            {
                "item_code": TEST_ITEM,
                "qty": 1,
                "uom": "Dozen",
                "rate": 1224,
                "warehouse": "Stores - DD",
            }
        ],
    }
    response = client.post("/api/resource/Sales Invoice", json=payload)
    if response.status_code != 200:
        print("  invoice creation error:", response.status_code, response.text[:160])
        return False
    return True


def cleanup_probe_invoices(admin: httpx.Client) -> None:
    rows = (
        admin.get(
            "/api/resource/Sales Invoice",
            params={
                "filters": json.dumps([["remarks", "=", PROBE_REMARK]]),
                "fields": '["name"]',
            },
        )
        .json()
        .get("data")
        or []
    )
    for row in rows:
        admin.delete(f"/api/resource/Sales Invoice/{row['name']}")


def main() -> int:
    if not (BASE and ADMIN_USER and ADMIN_PASSWORD and TEST_PASSWORD):
        print("Set ERPNEXT_URL, ERPNEXT_USER, ERPNEXT_PASSWORD and DIVA_TEST_PASSWORD")
        return 2

    admin = httpx.Client(base_url=BASE, timeout=30)
    admin.post(
        "/api/method/login", data={"usr": ADMIN_USER, "pwd": ADMIN_PASSWORD}
    ).raise_for_status()

    for email, spec in USERS.items():
        ensure_user(admin, email, spec)

    checks: dict[str, Any] = {
        "Price List write": can_write_price_list,
        "Sales Invoice list": lambda c: can_list(c, "Sales Invoice"),
        "Payment Entry list": lambda c: can_list(c, "Payment Entry"),
        "Stock Reconciliation list": lambda c: can_list(c, "Stock Reconciliation"),
        "Journal Entry list": lambda c: can_list(c, "Journal Entry"),
        "POS Profile list": lambda c: can_list(c, "POS Profile"),
        "User create": lambda c: can_create_user(admin, c),
        "Sales Invoice create (draft)": can_create_invoice,
    }

    results: dict[str, dict[str, bool]] = {}
    for email in USERS:
        client = client_for(email)
        print(email)
        results[email] = {}
        for label, check in checks.items():
            allowed = bool(check(client))
            results[email][label] = allowed
            print(f"  {label}: {allowed}")
        client.close()

    cleanup_probe_invoices(admin)

    manager = results["manager@diva.test"]
    cashier = results["cashier@diva.test"]
    expectations = [
        ("cashier cannot edit price lists", not cashier["Price List write"]),
        ("manager can edit price lists", manager["Price List write"]),
        ("cashier cannot list Stock Reconciliation", not cashier["Stock Reconciliation list"]),
        ("manager can list Stock Reconciliation", manager["Stock Reconciliation list"]),
        ("cashier cannot list Journal Entry", not cashier["Journal Entry list"]),
        ("manager can list Journal Entry", manager["Journal Entry list"]),
        ("cashier cannot create users", not cashier["User create"]),
        ("cashier can create invoices", cashier["Sales Invoice create (draft)"]),
        ("cashier can open the POS (POS Profile)", cashier["POS Profile list"]),
        ("manager can list invoices", manager["Sales Invoice list"]),
        ("manager can list payment entries", manager["Payment Entry list"]),
    ]

    failed = False
    for label, ok in expectations:
        print(("OK   " if ok else "FAIL ") + label)
        failed = failed or not ok

    admin.close()
    if failed:
        print("E-16 permission baseline FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
