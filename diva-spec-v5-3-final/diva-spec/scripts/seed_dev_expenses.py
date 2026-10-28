#!/usr/bin/env python3
"""Seed synthetic expenses and reconcile the daily cash closing (TASK-E-10).

Expenses are Journal Entries (cash or bank) against expense accounts, as allowed
by docs/05a section 8. Idempotent: each seeded entry carries a marker in
`user_remark`; submitted entries are skipped, drafts are submitted.

Credentials from the environment; all data is synthetic:
  ERPNEXT_URL=... ERPNEXT_USER=... ERPNEXT_PASSWORD=... python3 scripts/seed_dev_expenses.py

Never run against production. Prerequisites on the dev site: company "Diva Dev",
accounts "Cash - DD", "Diva Bank - DD", "Indirect Expenses - DD" and cost center
"Main - DD".
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
DATE = "2026-10-28"
CASH = f"Cash - {ABBR}"
BANK = f"Diva Bank - {ABBR}"
COST_CENTER = f"Main - {ABBR}"
MARKER = "DIVA-EXPENSE-SEED"

# account name, amount, paid-from account
EXPENSES = [
    ("Shop Rent", "750.00", CASH, "إيجار المحل"),
    ("Utilities", "320.50", CASH, "كهرباء ومياه"),
    ("Packaging", "180.00", CASH, "تغليف"),
    ("Marketing", "500.00", BANK, "تسويق"),
    ("Maintenance", "240.00", CASH, "صيانة"),
]

http = httpx.Client(base_url=BASE, timeout=30)
http.post("/api/method/login", data={"usr": USER, "pwd": PASSWORD}).raise_for_status()


def ensure_account(account_name: str) -> str:
    name = f"{account_name} - {ABBR}"
    if http.get(f"/api/resource/Account/{name}").status_code == 200:
        return name
    response = http.post(
        "/api/resource/Account",
        json={
            "account_name": account_name,
            "parent_account": f"Indirect Expenses - {ABBR}",
            "company": COMPANY,
            "is_group": 0,
            "account_type": "Expense Account",
        },
    )
    response.raise_for_status()
    print("account created:", name)
    return name


def find_entry(remark: str) -> dict[str, Any] | None:
    rows = (
        http.get(
            "/api/resource/Journal Entry",
            params={
                "filters": json.dumps([["user_remark", "=", remark], ["docstatus", "in", [0, 1]]]),
                "fields": '["name","docstatus"]',
                "limit_page_length": "1",
            },
        )
        .json()
        .get("data")
        or []
    )
    if not rows:
        return None
    return cast(dict[str, Any], rows[0])


def submit(name: str) -> dict[str, Any]:
    doc = http.get(f"/api/resource/Journal Entry/{name}").json()["data"]
    response = http.post("/api/method/frappe.client.submit", data={"doc": json.dumps(doc)})
    response.raise_for_status()
    return cast(dict[str, Any], response.json()["message"])


for account_name, amount, paid_from, arabic_note in EXPENSES:
    expense_account = ensure_account(account_name)
    remark = f"{MARKER}: {account_name} / {arabic_note}"
    existing = find_entry(remark)
    if existing is None:
        payload = {
            "voucher_type": "Cash Entry" if paid_from == CASH else "Bank Entry",
            "company": COMPANY,
            "posting_date": DATE,
            "user_remark": remark,
            "accounts": [
                {
                    "account": expense_account,
                    "debit_in_account_currency": float(amount),
                    "cost_center": COST_CENTER,
                },
                {
                    "account": paid_from,
                    "credit_in_account_currency": float(amount),
                },
            ],
        }
        if paid_from == BANK:
            payload["cheque_no"] = f"EXP-{account_name.upper().replace(' ', '-')}"
            payload["cheque_date"] = DATE
        response = http.post("/api/resource/Journal Entry", json=payload)
        response.raise_for_status()
        existing = {"name": response.json()["data"]["name"], "docstatus": 0}
        print("expense created:", account_name, amount)
    if existing["docstatus"] == 0:
        if paid_from == BANK:
            # A draft may predate the bank reference fields; make it submittable.
            http.put(
                f"/api/resource/Journal Entry/{existing['name']}",
                json={
                    "cheque_no": f"EXP-{account_name.upper().replace(' ', '-')}",
                    "cheque_date": DATE,
                },
            ).raise_for_status()
        submit(existing["name"])
        print("expense submitted:", existing["name"])
    else:
        print("expense exists:", existing["name"])

# --- Reconciliation: cash and bank movements on the day vs the ledger ---------


def gl_rows(account: str) -> list[dict[str, Any]]:
    return (
        http.get(
            "/api/resource/GL Entry",
            params={
                "filters": json.dumps([["account", "=", account], ["is_cancelled", "=", 0]]),
                "fields": '["posting_date","debit","credit","voucher_type","voucher_no"]',
                "limit_page_length": "0",
            },
        )
        .json()
        .get("data")
        or []
    )


def movement(account: str) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    rows = gl_rows(account)
    opening = sum(
        (
            Decimal(str(row["debit"])) - Decimal(str(row["credit"]))
            for row in rows
            if row["posting_date"] < DATE
        ),
        Decimal("0"),
    )
    debit = sum(
        (Decimal(str(row["debit"])) for row in rows if row["posting_date"] == DATE),
        Decimal("0"),
    )
    credit = sum(
        (Decimal(str(row["credit"])) for row in rows if row["posting_date"] == DATE),
        Decimal("0"),
    )
    return opening, debit, credit, opening + debit - credit


def expense_total(account: str) -> tuple[Decimal, Decimal]:
    rows = gl_rows(account)
    debit = sum((Decimal(str(row["debit"])) for row in rows), Decimal("0"))
    credit = sum((Decimal(str(row["credit"])) for row in rows), Decimal("0"))
    return debit, credit


failed = False
for account in (CASH, BANK):
    opening, debit, credit, closing = movement(account)
    print(
        f"{account}: opening={opening} in={debit} out={credit} closing={closing} "
        f"(reconciles={opening + debit - credit == closing})"
    )
    failed = failed or opening + debit - credit != closing

for account_name, _, _, _ in EXPENSES:
    account = f"{account_name} - {ABBR}"
    debit, credit = expense_total(account)
    print(f"expense account {account}: debit={debit} credit={credit}")
    failed = failed or debit <= 0 or credit != 0

print("cash closing checklist:")
print(f"  1. opening cash: {movement(CASH)[0]}")
print(f"  2. cash receipts (ledger debits): {movement(CASH)[1]}")
print(f"  3. cash expenses (ledger credits): {movement(CASH)[2]}")
print(f"  4. expected closing: {movement(CASH)[3]}")
print("  5. count the drawer, record the difference, and attach the count sheet")
print("  6. sales totals are not cash received (only the cash GL lines count)")

if failed:
    print("E-10 cash reconciliation FAILED")
raise SystemExit(1 if failed else 0)
