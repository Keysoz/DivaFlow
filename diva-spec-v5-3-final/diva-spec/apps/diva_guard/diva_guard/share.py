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
from frappe.utils import formatdate

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


def _party_phone_for(
	party_type: str,
	party: str,
	contact_person: str = "",
	contact_mobile: str = "",
) -> str:
	"""The best phone for a party: document contact, its Contact, then the party."""
	phone = str(contact_mobile or "").strip()
	if phone:
		return phone
	contact = str(contact_person or "").strip()
	if contact:
		phone = frappe.db.get_value("Contact", contact, "mobile_no") or ""
		if not phone:
			phone = frappe.db.get_value("Contact", contact, "phone") or ""
	if phone:
		return str(phone)
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


def _party_phone(doctype: str, doc: Any) -> str:
	party_type, party = _party(doctype, doc)
	return _party_phone_for(
		party_type,
		party,
		str(doc.get("contact_person") or ""),
		str(doc.get("contact_mobile") or ""),
	)


def _missing_phone() -> None:
	frappe.throw(
		_("This party has no phone number. Add a mobile on the Customer/Supplier or its Contact first.")
	)


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
		_missing_phone()
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


def _company_name(company: str) -> str:
	if not company:
		company = str(frappe.defaults.get_global_default("company") or "")
	if not company:
		return ""
	return str(frappe.db.get_value("Company", company, "company_name") or company)


@frappe.whitelist()  # type: ignore[untyped-decorator]
def statement_share(
	party_type: str,
	party: str,
	from_date: str,
	to_date: str,
	company: str = "",
	language: str = "ar",
) -> dict[str, Any]:
	"""The wa.me link and ready message for a customer or supplier statement (E-18).

	The amounts stay in the printed statement; the message only names the party
	and the period, so no business rule is recomputed here.
	"""
	party_type = str(party_type or "").strip()
	if party_type not in ("Customer", "Supplier"):
		frappe.throw(_("A statement is shared for a Customer or a Supplier"))
	party = str(party or "").strip()
	if not party:
		frappe.throw(_("Choose a party before sharing the statement"))
	if not frappe.has_permission(party_type, "read", party):
		frappe.throw(_("You do not have permission to view this party"), frappe.PermissionError)
	if not from_date or not to_date:
		frappe.throw(_("Choose the statement period before sharing"))
	phone = _normalize_phone(_party_phone_for(party_type, party))
	if not phone:
		_missing_phone()
	company_name = _company_name(company)
	period = f"{formatdate(from_date, 'dd-mm-yyyy')} - {formatdate(to_date, 'dd-mm-yyyy')}"
	if language == "en":
		message = (
			f"Hello, this is the account statement for {party} from {company_name} for the period {period}."
		)
	else:
		message = (
			f"مرحبًا، هذا كشف حساب {party} من {company_name} للفترة من "
			f"{formatdate(from_date, 'dd-mm-yyyy')} إلى {formatdate(to_date, 'dd-mm-yyyy')}."
		)
	return {
		"party_type": party_type,
		"party": party,
		"from_date": from_date,
		"to_date": to_date,
		"phone": phone,
		"message": message,
		"wa_link": f"https://wa.me/{phone}?text={quote(message)}",
		"print_format": "Party Statement Print",
	}
