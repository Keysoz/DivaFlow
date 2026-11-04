"""Login landing for the shop staff (DEC-106).

Frappe calls the ``get_website_user_home_page`` hook while it computes the home
page after login (``frappe.auth.LoginManager.set_user_info`` ->
``frappe.website.utils.get_home_page``). Non-admin staff start on the Diva Store
dashboard; the Administrator and System Managers keep the standard Desk landing.
"""

from __future__ import annotations

import frappe

# The owner-facing route; the workspace is pinned in infra/erpnext-config/desk.yaml
# (name "Diva Store", module "Custom Reports").
DIVA_STORE_ROUTE = "/desk/custom-reports/diva-store"


def get_website_user_home_page(user: str | None = None) -> str | None:
	"""Return the Diva Store dashboard for every non-admin staff account.

	Returning None lets Frappe fall through to ``Website Settings.home_page``
	and then to ``/desk``.
	"""
	user = user or frappe.session.user
	if user in ("Administrator", "Guest"):
		return None
	if "System Manager" in frappe.get_roles(user):
		return None
	return DIVA_STORE_ROUTE
