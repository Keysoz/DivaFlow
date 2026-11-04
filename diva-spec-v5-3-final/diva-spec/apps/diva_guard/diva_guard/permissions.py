"""Visibility for the Diva Guard and POS Next app tiles (DEC-105).

On the Desk apps screen the Administrator / System Manager sees every app;
every other user sees ERPNext and Diva Store only. The shop staff reach the
till and the guard from the Diva Store dashboard tiles, not from the switcher.
"""

from __future__ import annotations

import frappe


def can_see_admin_apps() -> bool:
	"""True for the Administrator and System Managers only."""
	if frappe.session.user == "Administrator":
		return True
	if frappe.session.user == "Guest":
		return False
	return "System Manager" in frappe.get_roles()
