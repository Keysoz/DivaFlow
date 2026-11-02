"""The customer-facing prints carry the store "Message us" QR (ENH-C-09, DEC-97).

The QR encodes the store WhatsApp number from Diva Guard Settings through
``whatsapp_link()``; a customer scans it and starts a chat with the shop. Only
documents a customer receives carry it - never an internal purchase document.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRINT_DIR = ROOT / "infra" / "erpnext-config" / "print_formats"

CUSTOMER_FACING = [
    "diva_sales_invoice_a4.html",
    "diva_receipt_80mm.html",
    "diva_payment_receipt.html",
    "diva_customer_statement.html",
    "diva_supplier_statement.html",
]
INTERNAL = [
    "diva_purchase_invoice_a4.html",
    "diva_purchase_receipt_a4.html",
    "diva_journal_entry_a4.html",
]


def test_customer_prints_show_the_message_us_qr() -> None:
    for name in CUSTOMER_FACING:
        html = (PRINT_DIR / name).read_text(encoding="utf-8")
        assert "whatsapp_link()" in html, name
        assert "qr_svg(wa_link)" in html, name
        assert "راسلنا" in html and "Message us" in html, name


def test_internal_prints_do_not_carry_the_message_us_qr() -> None:
    for name in INTERNAL:
        html = (PRINT_DIR / name).read_text(encoding="utf-8")
        assert "whatsapp_link" not in html, name
        assert "Message us" not in html, name


def test_store_number_is_configurable_data_not_code() -> None:
    settings = (
        ROOT
        / "apps"
        / "diva_guard"
        / "diva_guard"
        / "diva_guard"
        / "doctype"
        / "diva_guard_settings"
        / "diva_guard_settings.json"
    )
    doctype = json.loads(settings.read_text(encoding="utf-8"))
    fields = {field["fieldname"] for field in doctype["fields"]}
    assert "whatsapp_number" in fields
    assert "whatsapp_number" in doctype["field_order"]

    seed = (ROOT / "scripts" / "seed_diva_guard.py").read_text(encoding="utf-8")
    assert '"whatsapp_number"' in seed

    helper = (ROOT / "apps" / "diva_guard" / "diva_guard" / "jinja_methods.py").read_text(
        encoding="utf-8"
    )
    assert "def whatsapp_link" in helper
    assert "Diva Guard Settings" in helper
    # One normalization rule for the share links and the QR.
    assert "from diva_guard.share import _normalize_phone" in helper
