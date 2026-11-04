"""Product Info page endpoint (DEC-95).

Resolve a scanned barcode or a typed item code/name to the card shown on the
staff Product Info page. Read-only: the page never writes, prices or moves
stock.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any
from urllib.parse import quote

import frappe  # type: ignore[import-not-found]
from frappe import _
from werkzeug.wrappers import Response

DEFAULT_PRICE_LIST = "Standard Selling"

_MEDIA_TYPES = ("image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml")


def _resolve_item(query: str) -> str | None:
	"""Item code (exact) or barcode (Item Barcode / custom_barcode)."""
	if frappe.db.exists("Item", query):
		return query
	parent = frappe.db.get_value("Item Barcode", {"barcode": query}, "parent")
	if parent:
		return str(parent)
	parent = frappe.db.get_value("Item", {"custom_barcode": query}, "name")
	return str(parent) if parent else None


def image_endpoint_url(item_code: str) -> str:
	"""Authorized URL for the card image; hotlinking /private/files/ 403s."""

	return "/api/method/diva_guard.product_info.product_info_image?item_code=" + quote(item_code, safe="")


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
		# Streamed through the staff-only image endpoint below: the old relative
		# file URL (e.g. /private/files/...) answers 403 when the File record is
		# missing and leaks unrelated private files to anyone with File access.
		"image": image_endpoint_url(item.name) if item.get("image") else "",
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


def _item_image_file(item_code: str) -> Path | None:
	"""The site path of the item image, or None when none/unknown.

	Only the local-storage forms are allowed ("/private/files/X",
	"/files/X"), the resolved path must stay inside the site's files
	directory so a crafted Item image URL cannot read other files, and the
	type must be a supported image.
	"""
	image_url = str(frappe.db.get_value("Item", item_code, "image") or "").strip()
	if image_url.startswith("/private/files/"):
		relative = image_url.removeprefix("/private/files/")
		base_directories = (Path(frappe.utils.get_site_path("private", "files")),)
	elif image_url.startswith("/files/"):
		relative = image_url.removeprefix("/files/")
		base_directories = (
			Path(frappe.utils.get_site_path("public", "files")),
			Path(frappe.utils.get_site_path("assets")),
		)
	else:
		return None
	if not relative:
		return None

	file_name = Path(relative)
	if ".." in file_name.parts or file_name.is_absolute():
		return None
	for base in base_directories:
		candidate = (base / file_name).resolve()
		if base.resolve() in candidate.parents and candidate.is_file():
			return candidate
	return None


def _image_response(item_code: str) -> Response:
	"""The authorized streaming response for the item image (see above)."""

	file_path = _item_image_file(item_code) if frappe.db.exists("Item", item_code) else None
	mimetype = mimetypes.guess_type(str(file_path))[0] if file_path else None
	if (
		item_code
		and frappe.has_permission("Item", "read", item_code)
		and file_path
		and mimetype in _MEDIA_TYPES
	):
		response = Response(file_path.read_bytes(), status=200, mimetype=mimetype)
		response.headers["X-Content-Type-Options"] = "nosniff"
		response.headers["Cache-Control"] = "private, max-age=300"
		response.headers["Content-Disposition"] = f'inline; filename="{file_path.name}"'
		return response
	frappe.throw(_("No image is set for item {0}").format(item_code), frappe.DoesNotExistError)
	return Response()  # frappe.throw(...) never returns; keeps the type checker happy


@frappe.whitelist()  # type: ignore[untyped-decorator]
def product_info_image(item_code: str) -> Response:
	"""Stream the item image for the Product Info card.

	The card cannot hotlink `/private/files/...`: that route answers 403
	unless a File record exists. This staff-only endpoint re-checks Item
	read permission and serves only the item's own image (DEC-95: the page
	never writes; it only reads what the operator may already see).
	"""
	item_code = (item_code or "").strip()
	if not item_code or not frappe.db.exists("Item", item_code):
		frappe.throw(_("Item {0} not found").format(item_code), frappe.DoesNotExistError)
	if not frappe.has_permission("Item", "read", item_code):
		frappe.throw(_("You do not have permission to view items"), frappe.PermissionError)
	return _image_response(item_code)


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
