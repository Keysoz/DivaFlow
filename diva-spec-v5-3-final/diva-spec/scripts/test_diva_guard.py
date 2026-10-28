#!/usr/bin/env python3
"""Integration checks for diva_guard server rules (TASK-E-14a).

Runs against the disposable dev site with real staff accounts (E-16) and the
synthetic item/price data (E-06/E-09). Requires the diva_guard app installed and
seeded (scripts/seed_diva_guard.py). The manager PIN comes from the environment:

  ERPNEXT_URL=... ERPNEXT_USER=... ERPNEXT_PASSWORD=... DIVA_TEST_PASSWORD=... \
  DIVA_MANAGER_PIN=... python3 scripts/test_diva_guard.py
"""

import os
import sys
from typing import Any

import httpx

BASE = os.environ.get("ERPNEXT_URL", "").rstrip("/")
ADMIN_USER = os.environ.get("ERPNEXT_USER", "")
ADMIN_PASSWORD = os.environ.get("ERPNEXT_PASSWORD", "")
TEST_PASSWORD = os.environ.get("DIVA_TEST_PASSWORD", "")
MANAGER_PIN = os.environ.get("DIVA_MANAGER_PIN", "")
if not (BASE and ADMIN_USER and ADMIN_PASSWORD and TEST_PASSWORD and MANAGER_PIN):
    sys.exit(
        "Set ERPNEXT_URL, ERPNEXT_USER, ERPNEXT_PASSWORD, DIVA_TEST_PASSWORD and DIVA_MANAGER_PIN"
    )

COMPANY = "Diva Dev"
CUSTOMER = "Bulk Customer 01"
ITEM = "BULK-ACC-01"
WAREHOUSE = "Main Inventory - DD"
PRICE = 1224.0

admin = httpx.Client(base_url=BASE, timeout=30)
admin.post("/api/method/login", data={"usr": ADMIN_USER, "pwd": ADMIN_PASSWORD}).raise_for_status()


def login(email: str) -> httpx.Client:
    client = httpx.Client(base_url=BASE, timeout=30)
    client.post("/api/method/login", data={"usr": email, "pwd": TEST_PASSWORD}).raise_for_status()
    return client


def invoice_payload(qty: float, rate: float, paid: float) -> dict[str, Any]:
    return {
        "is_pos": 1,
        "pos_profile": "P003 POS",
        "customer": CUSTOMER,
        "company": COMPANY,
        "currency": "EGP",
        "conversion_rate": 1,
        "update_stock": 1,
        "selling_price_list": "Standard Selling",
        "price_list_currency": "EGP",
        "plc_conversion_rate": 1,
        "remarks": "E-14a guard test",
        "items": [
            {
                "item_code": ITEM,
                "qty": qty,
                "uom": "Dozen",
                "warehouse": WAREHOUSE,
                "rate": rate,
            }
        ],
        "payments": [{"mode_of_payment": "Cash", "amount": paid}],
    }


def create(
    client: httpx.Client, payload: dict[str, Any], token: str | None = None
) -> httpx.Response:
    headers = {"X-Diva-Override-Token": token} if token else {}
    response = client.post("/api/resource/Sales Invoice", json=payload, headers=headers)
    return response


def message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text
    if "_server_messages" in payload:
        return str(payload["_server_messages"])
    return str(payload.get("exception") or payload)[:400]


def cleanup() -> None:
    rows = (
        admin.get(
            "/api/resource/Sales Invoice",
            params={
                "filters": '[["remarks","=","E-14a guard test"]]',
                "fields": '["name"]',
                "limit_page_length": "0",
            },
        )
        .json()
        .get("data")
        or []
    )
    for row in rows:
        admin.delete(f"/api/resource/Sales Invoice/{row['name']}")


cashier = login("cashier@diva.test")
manager = login("manager@diva.test")
created: list[str] = []
failed = False


def expect(label: str, response: httpx.Response, *, ok: bool, contains: str = "") -> None:
    global failed
    is_ok = response.status_code == 200
    text = message(response)
    passed = is_ok == ok and (contains.lower() in text.lower() if contains else True)
    print(("OK   " if passed else "FAIL ") + label + f" [{response.status_code}] {text[:160]}")
    if is_ok and response.status_code == 200:
        created.append(response.json()["data"]["name"])
    failed = failed or not passed


# 1. MOQ: one Dozen is below the two-Dozen minimum.
expect(
    "cashier rejected below MOQ",
    create(cashier, invoice_payload(1, PRICE, PRICE)),
    ok=False,
    contains="Minimum quantity",
)

# 2. A compliant cashier sale passes and can be cleaned up.
expect(
    "cashier sale at list price passes",
    create(cashier, invoice_payload(2, PRICE, PRICE * 2)),
    ok=True,
)

# 3. 10% is above the cashier limit (5%) and needs a manager PIN.
discounted = invoice_payload(2, PRICE * 0.9, PRICE * 0.9 * 2)
expect(
    "cashier discount above 5% needs a manager PIN",
    create(cashier, discounted),
    ok=False,
    contains="manager PIN",
)

# 4. A manager can approve the same discount directly.
expect("manager discount above 5% passes", create(manager, discounted), ok=True)

# 5. The cashier can use a single-use approval token issued after a valid PIN.
approval = cashier.post(
    "/api/method/diva_guard.api.approve_discount",
    data={
        "pin": MANAGER_PIN,
        "reason": "Synthetic E-14a test",
        "discount_percent": 10,
        "amount": PRICE * 2 * 0.1,
        "voucher_doctype": "Sales Invoice",
    },
)
if approval.status_code != 200:
    print("FAIL approval API", approval.status_code, approval.text[:300])
    failed = True
    token = None
else:
    token = approval.json()["message"]["token"]
    expect(
        "cashier discount with manager approval passes", create(cashier, discounted, token), ok=True
    )
    expect(
        "approval token is single-use",
        create(cashier, discounted, token or ""),
        ok=False,
        contains="manager PIN",
    )

# 6. A counter invoice must be paid in full.
expect(
    "counter partial payment is rejected",
    create(cashier, invoice_payload(2, PRICE, PRICE)),
    ok=False,
    contains="paid in full",
)

# 7. A rate above the price list is rejected.
expect(
    "rate above the price list is rejected",
    create(cashier, invoice_payload(2, PRICE * 1.1, PRICE * 2 * 1.1 + 10)),
    ok=False,
    contains="above the price list",
)

# 8. A cashier cannot bypass the counter credit rule by omitting is_pos.
credit = invoice_payload(2, PRICE, PRICE * 2)
credit["is_pos"] = 0
credit.pop("payments")
credit["remarks"] = "E-14a guard test"
expect(
    "cashier cannot create a credit invoice",
    create(cashier, credit),
    ok=False,
    contains="paid in full",
)
expect("manager can create a credit invoice", create(manager, credit), ok=True)

cleanup()
cashier.close()
manager.close()
admin.close()

if failed:
    print("E-14a guard checks FAILED")
raise SystemExit(1 if failed else 0)
