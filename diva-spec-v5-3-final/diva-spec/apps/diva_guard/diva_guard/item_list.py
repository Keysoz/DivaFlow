"""Item list helpers (DEC-96).

The Item list shows the actual left stock across warehouses; Frappe lists do
not aggregate the Bin table, so the list view asks for the visible items here.
Read-only.
"""

from __future__ import annotations

import frappe  # type: ignore[import-not-found]
from frappe import _


@frappe.whitelist()  # type: ignore[untyped-decorator]
def left_stock(items: str | list[str]) -> dict[str, float]:
	"""Total actual quantity per item across all warehouses."""
	if isinstance(items, str):
		items = frappe.parse_json(items)
	if not items:
		return {}
	if not frappe.has_permission("Item", "read"):
		frappe.throw(_("You do not have permission to view items"), frappe.PermissionError)
	rows = frappe.get_list(
		"Bin",
		filters={"item_code": ["in", list(items)], "actual_qty": [">", 0]},
		fields=["item_code", "actual_qty"],
		limit_page_length=0,
	)
	totals: dict[str, float] = {}
	for row in rows:
		item_code = str(row["item_code"])
		totals[item_code] = totals.get(item_code, 0.0) + float(row["actual_qty"] or 0)
	return totals
