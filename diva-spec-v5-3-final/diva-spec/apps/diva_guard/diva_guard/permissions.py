"""Role-based visibility for the Diva app tiles (ENH-E-05).

``frappe.permissions.check_app_permission`` lets only System Managers see an
app. The shop's cashier and managers need the Diva and POS Next tiles, while
the Diva Guard settings stay with the managers. These functions are referenced
from each app's ``add_to_apps_screen`` entry.
"""

from __future__ import annotations

import frappe

# Cashier + managers: POS Next and the Diva (Store / Reports) apps.
DESK_ROLES = frozenset(
	{
		"System Manager",
		"Sales Manager",
		"Sales Master Manager",
		"Purchase Manager",
		"Stock Manager",
		"Accounts Manager",
		"Accounts User",
		"Sales User",
		"Stock User",
		"POSNext Cashier",
	}
)

# Managers only: the Diva Guard settings and approvals.
GUARD_ROLES = frozenset(
	{
		"System Manager",
		"Sales Manager",
		"Sales Master Manager",
		"Purchase Manager",
		"Stock Manager",
		"Accounts Manager",
		"Accounts User",
	}
)


def _has_any(roles: frozenset[str]) -> bool:
	if frappe.session.user == "Administrator":
		return True
	return bool(roles & set(frappe.get_roles(frappe.session.user)))


def can_use_pos_or_diva() -> bool:
	"""POS Next and the Diva (Store / Reports) tiles: cashier and managers."""
	return _has_any(DESK_ROLES)


def can_manage_diva_guard() -> bool:
	"""The Diva Guard settings tile: managers only."""
	return _has_any(GUARD_ROLES)
