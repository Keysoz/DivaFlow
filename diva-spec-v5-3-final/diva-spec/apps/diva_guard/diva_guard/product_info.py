"""Product Info page endpoint (DEC-95).

Resolve a scanned barcode or a typed item code/name to the card shown on the
staff Product Info page. Read-only: the page never writes, prices or moves
stock.
"""

from __future__ import annotations

from typing import Any

import frappe  # type: ignore[import-not-found]
from frappe import _

DEFAULT_PRICE_LIST = "Standard Selling"


def _resolve_item(query: str) -> str | None:
	"""Item code (exact) or barcode (Item Barcode / custom_barcode)."""
	if frappe.db.exists("Item", query):
		return query
	parent = frappe.db.get_value("Item Barcode", {"barcode": query}, "parent")
	if parent:
		return str(parent)
	parent = frappe.db.get_value("Item", {"custom_barcode": query}, "name")
	return str(parent) if parent else None


def _item_card(item_code: str) -> dict[str, Any]:
	item = frappe.get_doc("Item", item_code)
	barcodes = [row.barcode for row in item.get("barcodes") or [] if row.barcode]
	barcode = barcodes[0] if barcodes else str(item.get("custom_barcode") or "")

	prices = frappe.get_all(
		"Item Price",
		filters={"item_code": item_code, "price_list": DEFAULT_PRICE_LIST},
		fields=["uom", "price_list_rate"],
		limit_page_length=0,
	)
	price_by_uom = {str(row.uom): float(row.price_list_rate or 0) for row in prices}
	price_dozen = price_by_uom.get("Dozen")
	price_nos = price_by_uom.get("Nos")
	if price_nos is None and price_dozen:
		# Older items may only carry the Dozen row; show the per-piece price.
		price_nos = round(price_dozen / 12, 2)

	bins = frappe.get_all(
		"Bin",
		filters={"item_code": item_code, "actual_qty": [">", 0]},
		fields=["warehouse", "actual_qty", "stock_uom"],
		order_by="actual_qty desc",
		limit_page_length=0,
	)

	return {
		"item_code": item.name,
		"item_name": item.item_name,
		"item_group": item.item_group,
		"barcode": barcode,
		# Keep the file URL relative: the page is served from the same site, and an
		# absolute URL built from the site host may drop the port (e.g. :8080).
		"image": item.get("image") or "",
		"stock_uom": item.stock_uom,
		"price_dozen": price_dozen,
		"price_nos": price_nos,
		"total_stock": sum(float(row.actual_qty or 0) for row in bins),
		"bins": [
			{
				"warehouse": row.warehouse,
				"qty": float(row.actual_qty or 0),
				"uom": row.stock_uom,
			}
			for row in bins
		],
	}


@frappe.whitelist()  # type: ignore[untyped-decorator]
def product_info(query: str) -> dict[str, Any]:
	"""Barcode or item code -> one card; otherwise search matches to pick from."""
	query = (query or "").strip()
	if not query:
		return {"matched": False, "matches": []}

	if not frappe.has_permission("Item", "read"):
		frappe.throw(_("You do not have permission to view items"), frappe.PermissionError)

	item_code = _resolve_item(query)
	if item_code and frappe.has_permission("Item", "read", item_code):
		return {"matched": True, "item": _item_card(item_code)}

	like = f"%{query}%"
	matches = frappe.get_list(
		"Item",
		or_filters=[["item_code", "like", like], ["item_name", "like", like]],
		fields=["item_code", "item_name", "item_group"],
		limit_page_length=10,
	)
	return {"matched": False, "matches": matches}
