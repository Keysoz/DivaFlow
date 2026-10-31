"""Invoice sharing, level 1 (E-18, DEC-97).

Builds the free `wa.me` link with a normalized Egyptian number and a ready
Arabic or English message. The staff attach the downloaded PDF. Read-only.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

import frappe  # type: ignore[import-not-found]
from frappe import _

PRINT_FORMATS = {
	"Sales Invoice": "Diva Sales Invoice A4",
	"Purchase Invoice": "Diva Purchase Invoice A4",
	"Payment Entry": "Diva Payment Receipt",
}
LABELS = {
	"Sales Invoice": ("فاتورة بيع", "Sales Invoice"),
	"Purchase Invoice": ("فاتورة شراء", "Purchase Invoice"),
	"Payment Entry": ("إيصال دفع", "Payment Receipt"),
}


def _normalize_phone(phone: str) -> str:
	"""Digits for wa.me, with the Egyptian country code when missing."""
	digits = re.sub(r"\D", "", phone or "")
	if not digits:
		return ""
	if digits.startswith("00"):
		digits = digits[2:]
	if digits.startswith("20"):
		# "+20-01018782245" keeps the trunk 0 after the country code.
		if len(digits) > 3 and digits[2] == "0":
			return "20" + digits[3:]
		return digits
	if digits.startswith("0"):
		return "20" + digits[1:]
	if len(digits) == 10:
		return "20" + digits
	return digits


def _party(doctype: str, doc: Any) -> tuple[str, str]:
	if doctype == "Payment Entry":
		return str(doc.party_type), str(doc.party)
	if doctype == "Sales Invoice":
		return "Customer", str(doc.customer)
	return "Supplier", str(doc.supplier)


def _party_phone(doctype: str, doc: Any) -> str:
	phone = str(doc.get("contact_mobile") or "").strip()
	if phone:
		return phone
	contact = str(doc.get("contact_person") or "").strip()
	if contact:
		phone = frappe.db.get_value("Contact", contact, "mobile_no") or ""
		if not phone:
			phone = frappe.db.get_value("Contact", contact, "phone") or ""
	if phone:
		return str(phone)
	party_type, party = _party(doctype, doc)
	phone = frappe.db.get_value(party_type, party, "mobile_no") or ""
	if phone:
		return str(phone)
	contacts = frappe.get_all(
		"Dynamic Link",
		filters={"link_doctype": party_type, "link_name": party, "parenttype": "Contact"},
		pluck="parent",
		limit_page_length=5,
	)
	for row in contacts:
		phone = frappe.db.get_value("Contact", row, "mobile_no") or frappe.db.get_value(
			"Contact", row, "phone"
		)
		if phone:
			return str(phone)
	return ""


def _message(doctype: str, doc: Any, language: str) -> str:
	arabic, english = LABELS[doctype]
	company = frappe.db.get_value("Company", doc.company, "company_name") or doc.company
	currency = (
		doc.get("currency") or frappe.get_cached_value("Company", doc.company, "default_currency") or "EGP"
	)
	amount = doc.get("paid_amount") if doctype == "Payment Entry" else doc.get("grand_total")
	if language == "en":
		return f"Hello, here is {english} {doc.name} from {company} for {float(amount or 0):,.2f} {currency}."
	return f"مرحبًا، هذه {arabic} رقم {doc.name} من {company} بمبلغ {float(amount or 0):,.2f} {currency}."


@frappe.whitelist()  # type: ignore[untyped-decorator]
def invoice_share(doctype: str, name: str, language: str = "ar") -> dict[str, Any]:
	"""The wa.me link, ready message and print format for one document."""
	if doctype not in PRINT_FORMATS:
		frappe.throw(_("Invoice sharing is available for Sales Invoice, Purchase Invoice and Payment Entry"))
	if not frappe.has_permission(doctype, "read", name):
		frappe.throw(_("You do not have permission to view this document"), frappe.PermissionError)
	doc = frappe.get_doc(doctype, name)
	phone = _normalize_phone(_party_phone(doctype, doc))
	if not phone:
		frappe.throw(
			_("This party has no phone number. Add a mobile on the Customer/Supplier or its Contact first.")
		)
	party_type, party = _party(doctype, doc)
	message = _message(doctype, doc, "en" if language == "en" else "ar")
	return {
		"doctype": doctype,
		"name": doc.name,
		"party_type": party_type,
		"party": party,
		"phone": phone,
		"message": message,
		"wa_link": f"https://wa.me/{phone}?text={quote(message)}",
		"print_format": PRINT_FORMATS[doctype],
	}
