#!/usr/bin/env python3
"""Integration checks for diva_guard server rules (TASK-E-14a).

Runs against the disposable dev site with real staff accounts (E-16) and the
synthetic item/price data (E-06/E-09). Requires the diva_guard app installed and
seeded (scripts/seed_diva_guard.py). The manager PIN comes from the environment:

  ERPNEXT_URL=... ERPNEXT_USER=... ERPNEXT_PASSWORD=... DIVA_TEST_PASSWORD=... \
  DIVA_MANAGER_PIN=... python3 scripts/test_diva_guard.py
"""

import json
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


def submit_invoice(client: httpx.Client, name: str, token: str | None = None) -> httpx.Response:
    doc = client.get(f"/api/resource/Sales Invoice/{name}").json()["data"]
    headers = {"X-Diva-Override-Token": token} if token else {}
    return client.post(
        "/api/method/frappe.client.submit",
        data={"doc": json.dumps(doc)},
        headers=headers,
    )


def cleanup() -> None:
    rows = (
        admin.get(
            "/api/resource/Sales Invoice",
            params={
                "filters": '[["remarks","=","E-14a guard test"]]',
                "fields": '["name","docstatus"]',
                "limit_page_length": "0",
            },
        )
        .json()
        .get("data")
        or []
    )
    for row in rows:
        if row["docstatus"] == 1:
            admin.post(
                "/api/method/frappe.client.cancel",
                data={"doctype": "Sales Invoice", "name": row["name"]},
            )
        elif row["docstatus"] == 0:
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
    payload = response.json() if is_ok else {}
    data = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(data, dict) and data.get("name"):
        created.append(data["name"])
    failed = failed or not passed


# 1. MOQ: one Dozen is below the two-Dozen minimum.
expect(
    "cashier rejected below MOQ",
    create(cashier, invoice_payload(1, PRICE, PRICE)),
    ok=False,
    contains="Minimum quantity",
)

# 2. A compliant cashier sale can be created and submitted.
sale = create(cashier, invoice_payload(2, PRICE, PRICE * 2))
expect("cashier sale at list price passes", sale, ok=True)
sale_name = sale.json()["data"]["name"]
expect("cashier can submit a compliant invoice", submit_invoice(cashier, sale_name), ok=True)

# 3. 10% is above the cashier limit (5%): a draft may wait, submit must block.
discounted = invoice_payload(2, PRICE * 0.9, PRICE * 0.9 * 2)
discount_draft = create(cashier, discounted)
expect("cashier discount draft can wait for a manager", discount_draft, ok=True)
discount_name = discount_draft.json()["data"]["name"]
expect(
    "cashier discount above 5% needs a manager PIN to submit",
    submit_invoice(cashier, discount_name),
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
    approved_sale = create(cashier, discounted, token)
    expect("cashier discount with manager approval can be drafted", approved_sale, ok=True)
    approved_name = approved_sale.json()["data"]["name"]
    expect(
        "cashier discount with manager approval submits",
        submit_invoice(cashier, approved_name, token),
        ok=True,
    )
    replay = create(cashier, discounted, token or "")
    expect("a replayed approval token can be drafted", replay, ok=True)
    replay_name = replay.json()["data"]["name"]
    expect(
        "a replayed approval token cannot submit",
        submit_invoice(cashier, replay_name, token or ""),
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

# 9. A token minted by one user cannot be used by another user.
manager_approval = manager.post(
    "/api/method/diva_guard.api.approve_discount",
    data={
        "pin": MANAGER_PIN,
        "reason": "Wrong-user test",
        "discount_percent": 10,
        "amount": PRICE * 2 * 0.1,
        "voucher_doctype": "Sales Invoice",
    },
)
if manager_approval.status_code == 200:
    wrong_token = manager_approval.json()["message"]["token"]
    wrong_sale = create(cashier, discounted, wrong_token)
    wrong_name = wrong_sale.json()["data"]["name"] if wrong_sale.status_code == 200 else ""
    expect(
        "a token minted by another user is rejected",
        submit_invoice(cashier, wrong_name, wrong_token) if wrong_name else wrong_sale,
        ok=False,
        contains="manager PIN",
    )
else:
    print("FAIL manager approval API", manager_approval.status_code, manager_approval.text[:200])
    failed = True

# 10. The approval ceiling must cover the actual discount.
ceiling = cashier.post(
    "/api/method/diva_guard.api.approve_discount",
    data={
        "pin": MANAGER_PIN,
        "reason": "Ceiling test",
        "discount_percent": 5,
        "amount": PRICE * 2 * 0.05,
        "voucher_doctype": "Sales Invoice",
    },
)
if ceiling.status_code == 200:
    ceiling_token = ceiling.json()["message"]["token"]
    ceiling_sale = create(cashier, discounted, ceiling_token)
    ceiling_name = ceiling_sale.json()["data"]["name"] if ceiling_sale.status_code == 200 else ""
    expect(
        "an approval below the actual discount is rejected",
        submit_invoice(cashier, ceiling_name, ceiling_token) if ceiling_name else ceiling_sale,
        ok=False,
        contains="manager PIN",
    )
else:
    print("FAIL ceiling approval API", ceiling.status_code, ceiling.text[:200])
    failed = True

# 10b. An expired approval token is rejected.
expiring = cashier.post(
    "/api/method/diva_guard.api.approve_discount",
    data={
        "pin": MANAGER_PIN,
        "reason": "Expiry test",
        "discount_percent": 10,
        "amount": PRICE * 2 * 0.1,
        "voucher_doctype": "Sales Invoice",
    },
)
if expiring.status_code == 200:
    expiry_payload = expiring.json()["message"]
    admin.put(
        f"/api/resource/Diva Override Approval/{expiry_payload['name']}",
        json={"expires_at": "2020-01-01 00:00:00"},
    )
    expiry_sale = create(cashier, discounted, expiry_payload["token"])
    expiry_name = expiry_sale.json()["data"]["name"] if expiry_sale.status_code == 200 else ""
    expect(
        "an expired approval token is rejected",
        submit_invoice(cashier, expiry_name, expiry_payload["token"])
        if expiry_name
        else expiry_sale,
        ok=False,
        contains="manager PIN",
    )
else:
    print("FAIL expiry approval API", expiring.status_code, expiring.text[:200])
    failed = True

# 11. A missing Nos price must not fall back to the client price.
nos = invoice_payload(24, 1, 24)
nos["items"][0]["uom"] = "Nos"
expect(
    "a Nos line uses the Dozen price, not the client rate",
    create(cashier, nos),
    ok=False,
    contains="discount",
)

# 12. Negative quantities and free items are rejected for cashiers.
negative = invoice_payload(-2, PRICE, 0)
expect("negative quantity is rejected", create(cashier, negative), ok=False, contains="grand total")
free = invoice_payload(2, 0, PRICE * 2)
free["items"][0]["is_free_item"] = 1
expect("free items need a manager", create(cashier, free), ok=False, contains="free items")

cleanup()
cashier.close()
manager.close()
admin.close()

if failed:
    print("E-14a guard checks FAILED")
raise SystemExit(1 if failed else 0)
