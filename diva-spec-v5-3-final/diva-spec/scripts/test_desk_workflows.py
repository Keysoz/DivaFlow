#!/usr/bin/env python3
"""Integration checks for the Diva Desk workflows (DEC-85 to DEC-90).

Runs against the disposable dev site. Covers the server half of the Desk layer:

1. Item creation the standard way: blank barcode auto-generates an internal
   EAN-13; Standard Selling prices per Dozen and Nos are written.
2. Item dialog backend: item + submitted opening-stock reconciliation.
3. Global search: Item code/name/group/barcode, Customer/Supplier phone, invoice id.
4. Purchase Receipt submit -> draft Purchase Invoice + draft Material Transfer to
   Stores - DD (the owner submits both manually).
5. Sales Invoice Pay: partial then full, Cash, nothing paid before the click.

Usage:
  ERPNEXT_URL=http://localhost:8080 ERPNEXT_USER=Administrator \
  ERPNEXT_PASSWORD=admin python3 scripts/test_desk_workflows.py
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
CUSTOMER = "Bulk Customer 01"
SUPPLIER = "Bulk Supplier 1"
ITEM = "RD-852"
SOURCE_WAREHOUSE = "Main Inventory - DD"
TARGET_WAREHOUSE = "Stores - DD"
STAMP = time.strftime("%H%M%S")
TEST_ITEM = f"DESK-{STAMP}"
STOCK_ITEM = f"DESK-STK-{STAMP}"
TEST_BARCODE_PHONE = f"+2010{STAMP}"

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
    if isinstance(payload, dict):
        server_messages = payload.get("_server_messages")
        if server_messages:
            try:
                messages = json.loads(server_messages)
                return " | ".join(json.loads(m).get("message", "") for m in messages)[:400]
            except (ValueError, TypeError):
                return str(server_messages)[:400]
        return str(payload.get("exception") or payload)[:400]
    return str(payload)[:400]


def call(method: str, **params: Any) -> httpx.Response:
    return http.post(f"/api/method/{method}", data={k: str(v) for k, v in params.items()})


def method_json(method: str, **params: Any) -> Any:
    response = call(method, **params)
    if response.status_code >= 400:
        raise RuntimeError(f"{method}: {error_of(response)}")
    return response.json().get("message")


def resource(doctype: str, name: str) -> dict[str, Any]:
    response = http.get(f"/api/resource/{doctype}/{name}")
    response.raise_for_status()
    return cast(dict[str, Any], response.json()["data"])


def list_rows(doctype: str, **params: Any) -> list[dict[str, Any]]:
    response = http.get(f"/api/resource/{doctype}", params=params)
    response.raise_for_status()
    return cast(list[dict[str, Any]], response.json().get("data", []))


def create(doctype: str, payload: dict[str, Any]) -> str:
    response = http.post(f"/api/resource/{doctype}", json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"create {doctype}: {error_of(response)}")
    name = response.json()["data"]["name"]
    created.append((doctype, name))
    return str(name)


def submit(doctype: str, name: str) -> None:
    doc = resource(doctype, name)
    response = http.post("/api/method/frappe.client.submit", data={"doc": json.dumps(doc)})
    if response.status_code >= 400:
        raise RuntimeError(f"submit {doctype} {name}: {error_of(response)}")


def ean13_valid(code: str) -> bool:
    if len(code) != 13 or not code.isdigit():
        return False
    total = sum(int(digit) * (3 if index % 2 else 1) for index, digit in enumerate(code[:12]))
    return (10 - total % 10) % 10 == int(code[12])


def item_prices(item_code: str) -> list[dict[str, Any]]:
    return list_rows(
        "Item Price",
        filters=json.dumps([["item_code", "=", item_code]]),
        fields='["price_list","uom","price_list_rate"]',
        limit_page_length=0,
    )


# ---------------------------------------------------------------------------
# 1. Standard Item creation: blank barcode is generated
# ---------------------------------------------------------------------------
def test_standard_item() -> str:
    print("\n1. Item creation (standard): blank barcode generated")
    item_code = create(
        "Item",
        {
            "item_code": TEST_ITEM,
            "item_name": f"Desk Test {STAMP}",
            "item_group": "Accessories",
            "stock_uom": "Nos",
            "is_stock_item": 1,
            "standard_rate": 1200,
            "custom_barcode": "",
        },
    )
    doc = resource("Item", item_code)
    barcodes = [row["barcode"] for row in doc.get("barcodes") or []]
    barcode = barcodes[0] if barcodes else ""
    expect(
        "blank barcode auto-generates a valid internal EAN-13",
        barcode.startswith("20") and ean13_valid(barcode),
        barcode,
    )
    expect(
        "stock UOM is Dozen and buying/selling UOM is Dozen (DEC-96)",
        doc["stock_uom"] == "Dozen"
        and doc["purchase_uom"] == "Dozen"
        and doc["sales_uom"] == "Dozen",
        doc.get("stock_uom"),
    )
    prices = item_prices(item_code)
    expect(
        "Standard Selling prices exist per Dozen and per Nos",
        any(row["price_list"] == "Standard Selling" and row["uom"] == "Dozen" for row in prices)
        and any(row["price_list"] == "Standard Selling" and row["uom"] == "Nos" for row in prices),
        prices,
    )

    duplicate = http.post(
        "/api/resource/Item",
        json={
            "item_code": item_code,
            "item_name": "Duplicate",
            "item_group": "Accessories",
            "stock_uom": "Nos",
            "is_stock_item": 1,
        },
    )
    expect(
        "the same item code cannot be created twice",
        duplicate.status_code >= 400,
        duplicate.text[:200],
    )
    return item_code


# ---------------------------------------------------------------------------
# 2. Item dialog backend: item + opening stock
# ---------------------------------------------------------------------------
def test_opening_stock_item() -> None:
    print("\n2. Item dialog backend: item + opening stock reconciliation")
    response = call(
        "diva_guard.desk_api.create_item_with_opening_stock",
        item_code=STOCK_ITEM,
        item_name=f"Desk Stock {STAMP}",
        item_group="Accessories",
        barcode="",
        selling_price=1200,
        wholesale_price=1000,
        buying_price=900,
        accepted_qty=2,
        warehouse=TARGET_WAREHOUSE,
    )
    if response.status_code >= 400:
        expect("item with opening stock is created", False, error_of(response))
        return
    result = response.json()["message"]
    created.append(("Item", result["item_code"]))
    created.append(("Stock Reconciliation", result["stock_reconciliation"]))
    bins = list_rows(
        "Bin",
        filters=json.dumps(
            [["item_code", "=", result["item_code"]], ["warehouse", "=", TARGET_WAREHOUSE]]
        ),
        fields='["actual_qty","valuation_rate"]',
    )
    expect(
        "the item has 2 Dozen at Stores - DD",
        bins and abs(float(bins[0]["actual_qty"]) - 2.0) < 0.001,
        bins,
    )
    expect(
        "valuation is the buying price per Dozen",
        bins and abs(float(bins[0]["valuation_rate"]) - 900.0) < 0.01,
        bins,
    )
    reconciliation = resource("Stock Reconciliation", result["stock_reconciliation"])
    expect(
        "the stock reconciliation is submitted",
        reconciliation["docstatus"] == 1,
        reconciliation["docstatus"],
    )
    wholesale = item_prices(result["item_code"])
    expect(
        "the Wholesale price list is written",
        any(row["price_list"] == "Wholesale" and row["uom"] == "Dozen" for row in wholesale),
        wholesale,
    )
    expect(
        "the blank barcode was generated",
        bool(result.get("barcode")) and ean13_valid(result["barcode"]),
        result.get("barcode"),
    )


# ---------------------------------------------------------------------------
# 3. Global search
# ---------------------------------------------------------------------------
def test_global_search(item_code: str) -> None:
    print("\n3. Global search (search bar / Ctrl+K)")

    def names(query: str, doctype: str) -> list[str]:
        response = call("diva_guard.desk_api.global_search", query=query)
        if response.status_code >= 400:
            print(error_of(response))
            return []
        return [row["name"] for row in response.json()["message"] if row["doctype"] == doctype]

    expect(
        "item found by code",
        any(item_code in name or name == item_code for name in names(item_code, "Item")),
    )
    expect("item found by name", bool(names("Desk Test", "Item")))
    expect("item found by item group", bool(names("Accessories", "Item")))

    barcode = resource("Item", item_code).get("barcodes") or []
    barcode_value = barcode[0]["barcode"] if barcode else ""
    expect("item found by barcode", bool(names(barcode_value, "Item")), barcode_value)

    contact = create(
        "Contact",
        {
            "first_name": f"Desk Phone {STAMP}",
            "phone_nos": [{"phone": TEST_BARCODE_PHONE, "is_primary_phone": 1}],
            "links": [{"link_doctype": "Customer", "link_name": CUSTOMER}],
        },
    )
    expect(
        "customer found by linked phone", CUSTOMER in names(TEST_BARCODE_PHONE, "Customer"), contact
    )

    supplier_phone = f"022{STAMP}"
    create(
        "Contact",
        {
            "first_name": f"Desk Supplier Phone {STAMP}",
            "phone_nos": [{"phone": supplier_phone, "is_primary_phone": 1}],
            "links": [{"link_doctype": "Supplier", "link_name": SUPPLIER}],
        },
    )
    expect(
        "supplier found by linked phone",
        SUPPLIER in names(supplier_phone, "Supplier"),
        supplier_phone,
    )

    invoice_name = list_rows("Sales Invoice", fields='["name"]', limit_page_length=1)
    if invoice_name:
        invoice_id = invoice_name[0]["name"]
        expect("invoice found by id", invoice_id in names(invoice_id, "Sales Invoice"), invoice_id)
        bar = http.post(
            "/api/method/frappe.desk.search.awesomebar_search", data={"txt": invoice_id}
        )
        expect(
            "search bar hook returns the invoice",
            bar.status_code < 400
            and any("Sales Invoice" in str(row) for row in bar.json().get("message", [])),
            bar.text[:200],
        )


# ---------------------------------------------------------------------------
# 4. Purchase Receipt: drafts only
# ---------------------------------------------------------------------------
def test_purchase_receipt(item_code: str) -> None:
    print("\n4. Purchase Receipt -> draft Purchase Invoice + draft Material Transfer")
    item_code = item_code or ITEM
    before = list_rows(
        "Bin",
        filters=json.dumps([["item_code", "=", item_code], ["warehouse", "=", TARGET_WAREHOUSE]]),
        fields='["actual_qty"]',
    )
    before_qty = float(before[0]["actual_qty"]) if before else 0.0

    receipt = create(
        "Purchase Receipt",
        {
            "supplier": SUPPLIER,
            "company": COMPANY,
            "posting_date": time.strftime("%Y-%m-%d"),
            "set_warehouse": SOURCE_WAREHOUSE,
            "currency": "EGP",
            "conversion_rate": 1,
            "remarks": f"desk test {STAMP}",
            "items": [
                {
                    "item_code": item_code,
                    "qty": 1,
                    "uom": "Dozen",
                    "conversion_factor": 1,
                    "rate": 1000,
                    "warehouse": SOURCE_WAREHOUSE,
                }
            ],
        },
    )
    submit("Purchase Receipt", receipt)
    receipt_doc = resource("Purchase Receipt", receipt)
    expected_stock = sum(float(row["stock_qty"]) for row in receipt_doc["items"])

    invoices = list_rows(
        "Purchase Invoice",
        filters=json.dumps([["bill_no", "=", receipt]]),
        fields='["name","docstatus","update_stock"]',
        limit_page_length=0,
    )
    expect("a Purchase Invoice is created automatically", bool(invoices), invoices)
    invoice_name = invoices[0]["name"] if invoices else ""
    if invoices:
        expect(
            "the Purchase Invoice is a draft (not auto-submitted)",
            int(invoices[0]["docstatus"]) == 0,
            invoices[0],
        )
        expect(
            "the Purchase Invoice does not post stock twice",
            int(invoices[0]["update_stock"]) == 0,
            invoices[0]["update_stock"],
        )

    entries = list_rows(
        "Stock Entry",
        filters=json.dumps([["purchase_receipt_no", "=", receipt]]),
        fields='["name","docstatus","stock_entry_type"]',
        limit_page_length=0,
    )
    expect("a Stock Entry is created automatically", bool(entries), entries)
    entry_name = entries[0]["name"] if entries else ""
    if entries:
        entry = resource("Stock Entry", entry_name)
        expect(
            "the Stock Entry is a draft (not auto-submitted)",
            entry["docstatus"] == 0,
            entry["docstatus"],
        )
        expect(
            "the Stock Entry is a Material Transfer",
            entry["stock_entry_type"] == "Material Transfer",
            entry["stock_entry_type"],
        )
        expect(
            "the Stock Entry targets Stores - DD",
            all(row["t_warehouse"] == TARGET_WAREHOUSE for row in entry["items"]),
            entry["items"],
        )
        moved = sum(float(row["qty"]) * float(row["conversion_factor"]) for row in entry["items"])
        expect(
            "the Stock Entry moves the whole received stock quantity",
            abs(moved - expected_stock) < 0.001,
            (moved, expected_stock),
        )
        expect(
            "a Dozen received on a Dozen item moves 1 Dozen",
            abs(expected_stock - 1.0) < 0.001 and abs(moved - 1.0) < 0.001,
            (expected_stock, moved),
        )

    # The owner submits the drafts manually; the stock moves only then.
    if entry_name:
        submit("Stock Entry", entry_name)
        expect(
            "the manual Stock Entry submit moves the stock",
            resource("Stock Entry", entry_name)["docstatus"] == 1,
        )
    if invoice_name:
        submit("Purchase Invoice", invoice_name)
        expect(
            "the manual Purchase Invoice submit succeeds",
            resource("Purchase Invoice", invoice_name)["docstatus"] == 1,
        )

    after = list_rows(
        "Bin",
        filters=json.dumps([["item_code", "=", item_code], ["warehouse", "=", TARGET_WAREHOUSE]]),
        fields='["actual_qty"]',
    )
    after_qty = float(after[0]["actual_qty"]) if after else 0.0
    expect(
        "Stores - DD received the whole received stock quantity",
        abs((after_qty - before_qty) - expected_stock) < 0.001,
        (before_qty, after_qty, expected_stock),
    )

    duplicates = list_rows(
        "Purchase Invoice",
        filters=json.dumps([["bill_no", "=", receipt]]),
        fields='["name"]',
        limit_page_length=0,
    )
    expect(
        "re-submitting does not duplicate the Purchase Invoice",
        len(duplicates) == len(invoices),
        duplicates,
    )


# ---------------------------------------------------------------------------
# 5. Sales Invoice Pay (nothing automatic)
# ---------------------------------------------------------------------------
def test_pay_invoice() -> None:
    print("\n5. Sales Invoice Pay: partial, then the rest, always Cash")
    price = list_rows(
        "Item Price",
        filters=json.dumps(
            [
                ["item_code", "=", ITEM],
                ["price_list", "=", "Standard Selling"],
                ["uom", "=", "Dozen"],
            ]
        ),
        fields='["price_list_rate"]',
    )
    rate = float(price[0]["price_list_rate"]) if price else 1200.0
    invoice = create(
        "Sales Invoice",
        {
            "customer": CUSTOMER,
            "company": COMPANY,
            "posting_date": time.strftime("%Y-%m-%d"),
            "currency": "EGP",
            "conversion_rate": 1,
            "selling_price_list": "Standard Selling",
            "price_list_currency": "EGP",
            "plc_conversion_rate": 1,
            "update_stock": 0,
            "remarks": f"desk pay test {STAMP}",
            "items": [
                {"item_code": ITEM, "qty": 1, "uom": "Dozen", "conversion_factor": 12, "rate": rate}
            ],
        },
    )
    submit("Sales Invoice", invoice)
    doc = resource("Sales Invoice", invoice)
    total = float(doc["grand_total"])
    expect(
        "the invoice is submitted and unpaid",
        doc["docstatus"] == 1 and abs(float(doc["outstanding_amount"]) - total) < 0.01,
        doc["outstanding_amount"],
    )

    payments = list_rows(
        "GL Entry",
        filters=json.dumps(
            [["against_voucher", "=", invoice], ["voucher_type", "=", "Payment Entry"]]
        ),
        fields='["name"]',
    )
    expect("submitting the invoice does not create a payment", not payments, payments)

    partial = method_json(
        "diva_guard.desk_api.pay_invoice",
        invoice_name=invoice,
        amount=round(total / 2, 2),
        mode_of_payment="Cash",
    )
    created.append(("Payment Entry", partial["payment_entry"]))
    entry = resource("Payment Entry", partial["payment_entry"])
    expect("the partial payment is submitted", entry["docstatus"] == 1, entry["docstatus"])
    expect(
        "the partial payment is Cash", entry["mode_of_payment"] == "Cash", entry["mode_of_payment"]
    )
    doc = resource("Sales Invoice", invoice)
    expect(
        "half the invoice is still outstanding",
        abs(float(doc["outstanding_amount"]) - (total - round(total / 2, 2))) < 0.02,
        doc["outstanding_amount"],
    )

    remaining = float(resource("Sales Invoice", invoice)["outstanding_amount"])
    rest = method_json(
        "diva_guard.desk_api.pay_invoice",
        invoice_name=invoice,
        amount=remaining,
        mode_of_payment="Cash",
    )
    created.append(("Payment Entry", rest["payment_entry"]))
    doc = resource("Sales Invoice", invoice)
    expect(
        "the invoice is fully paid after the second click",
        abs(float(doc["outstanding_amount"])) < 0.01,
        doc["outstanding_amount"],
    )
    expect("the invoice status is Paid", doc["status"] == "Paid", doc["status"])

    too_much = call(
        "diva_guard.desk_api.pay_invoice", invoice_name=invoice, amount=1, mode_of_payment="Cash"
    )
    expect("an over-payment is refused", too_much.status_code >= 400, error_of(too_much))

    draft = create(
        "Sales Invoice",
        {
            "customer": CUSTOMER,
            "company": COMPANY,
            "currency": "EGP",
            "conversion_rate": 1,
            "update_stock": 0,
            "items": [
                {"item_code": ITEM, "qty": 1, "uom": "Dozen", "conversion_factor": 12, "rate": rate}
            ],
        },
    )
    unpaid = call(
        "diva_guard.desk_api.pay_invoice", invoice_name=draft, amount=1, mode_of_payment="Cash"
    )
    expect("a draft invoice cannot be paid", unpaid.status_code >= 400, error_of(unpaid))


def cleanup() -> None:
    """Best effort: cancel and delete what this run created, newest first."""
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
        quick_item = test_standard_item()
        test_opening_stock_item()
        test_global_search(quick_item)
        test_purchase_receipt(quick_item)
        test_pay_invoice()
    finally:
        cleanup()
    print(f"\n{'FAILURES: ' + str(failures) if failures else 'all desk workflow checks passed'}")
    sys.exit(1 if failures else 0)
