"""Idempotent desk permission grants (ENH-E-05).

Frappe's standard roles alone do not guarantee desk access; POS Next ships
Custom DocPerm rows that shadow the standard table. ``ensure_desk_permissions``
uses Frappe's own ``add_permission`` (idempotent) to give the Sales User role
read access to invoices and payments, so the Diva Store invoice links and the
Pay flow are available to a user who only holds the standard sales roles.
"""

from __future__ import annotations

import frappe

CASHIER_ROLE = "Sales User"
DESK_READ_DOCTYPES = ("Sales Invoice", "Payment Entry")


@frappe.whitelist()  # type: ignore[untyped-decorator]
def ensure_desk_permissions() -> dict[str, list[str]]:
	"""Grant the Sales User role read on invoices and payments (idempotent)."""
	frappe.only_for("System Manager")
	granted: dict[str, list[str]] = {}
	for doctype in DESK_READ_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		frappe.permissions.add_permission(doctype, CASHIER_ROLE, permlevel=0)
		granted[doctype] = [CASHIER_ROLE]
	frappe.db.commit()
	return granted
