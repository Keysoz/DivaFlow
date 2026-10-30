"""Desk workflow endpoints and Purchase Receipt automation (DEC-85/86/87).

The client layer lives in ``diva_desk``; this module owns the server-side
permissions, validation and document creation. Nothing here verifies a payment:
:func:`pay_invoice` creates and submits a normal Payment Entry only when the
user clicks Pay, and the ``payment_reviewer`` step is untouched.
"""

from __future__ import annotations

from typing import Any

import frappe  # type: ignore[import-not-found]
from frappe import _
from frappe.utils import flt, today  # type: ignore[import-not-found]
from rules_engine import is_valid_ean13, next_internal_ean13

TARGET_WAREHOUSE = "Stores - DD"
DEFAULT_MODE_OF_PAYMENT = "Cash"


def _existing_barcodes() -> list[str]:
	"""Every barcode already used by an Item, so a generated one is never a duplicate."""
	values = frappe.get_all(
		"Item Barcode",
		pluck="barcode",
		limit_page_length=0,
	)
	extra = frappe.get_all(
		"Item",
		filters={"custom_barcode": ["is", "set"]},
		pluck="custom_barcode",
		limit_page_length=0,
	)
	return [str(value) for value in values + extra if value]


def _assert_barcode_free(barcode: str) -> None:
	owner = frappe.db.get_value("Item Barcode", {"barcode": barcode}, "parent")
	if not owner:
		owner = frappe.db.get_value("Item", {"custom_barcode": barcode}, "name")
	if owner:
		frappe.throw(
			_("Barcode {0} is already used by item {1}.").format(barcode, owner),
			frappe.ValidationError,
		)


@frappe.whitelist()  # type: ignore[untyped-decorator]
def create_quick_item(
	item_code: str,
	item_name: str,
	item_group: str,
	barcode: str = "",
	generate_barcode: int | bool = 0,
	buying_price: float | str = 0,
	selling_price: float | str = 0,
	accepted_qty: float | str = 0,
	warehouse: str = "",
) -> dict[str, Any]:
	"""Create a stock Item from the Purchase Receipt Add-Item dialog.

	The item is created in Nos (stock UOM) and bought/sold in Dozen (DEC-20).
	The selling price is the Dozen rate and is saved to the Standard Selling
	price list by ``diva_guard.events.sync_quick_price``. The buying price is
	kept on the Purchase Receipt line; there is no Standard Buying price list.
	"""
	if not frappe.has_permission("Item", "create"):
		frappe.throw(_("You do not have permission to create items"), frappe.PermissionError)

	item_code = (item_code or "").strip()
	item_name = (item_name or "").strip()
	item_group = (item_group or "").strip()
	if not item_code or not item_name:
		frappe.throw(_("Item Code and Item Name are required"))
	if frappe.db.exists("Item", item_code):
		frappe.throw(_("Item {0} already exists").format(item_code))
	if not item_group or not frappe.db.exists("Item Group", item_group):
		frappe.throw(_("Item Group {0} does not exist").format(item_group))

	selling = flt(selling_price)
	if selling <= 0:
		frappe.throw(_("Selling Price must be greater than zero"))
	buying = flt(buying_price)
	if buying < 0:
		frappe.throw(_("Buying Price cannot be negative"))
	qty = flt(accepted_qty)
	if qty <= 0:
		frappe.throw(_("Accepted Quantity must be greater than zero"))

	barcode = (barcode or "").strip()
	if barcode:
		if not is_valid_ean13(barcode):
			frappe.throw(_("Barcode {0} is not a valid EAN-13.").format(barcode))
		_assert_barcode_free(barcode)
	elif generate_barcode:
		barcode = next_internal_ean13(_existing_barcodes(), prefix=20)

	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": item_name,
			"item_group": item_group,
			"stock_uom": "Nos",
			"purchase_uom": "Dozen",
			"sales_uom": "Dozen",
			"is_stock_item": 1,
			"standard_rate": selling,
			"custom_barcode": barcode or None,
		}
	)
	item.insert(ignore_permissions=True)

	return {
		"item_code": item.name,
		"item_name": item.item_name,
		"item_group": item.item_group,
		"barcode": barcode,
		"buying_price": buying,
		"selling_price": selling,
		"accepted_qty": qty,
		"warehouse": warehouse or "",
	}


def _mode_account(mode_of_payment: str, company: str) -> str:
	rows = frappe.get_all(
		"Mode of Payment Account",
		filters={"parent": mode_of_payment, "company": company},
		fields=["default_account"],
		limit_page_length=1,
	)
	if not rows or not rows[0].get("default_account"):
		frappe.throw(_("Mode of Payment {0} has no account for {1}").format(mode_of_payment, company))
	return str(rows[0]["default_account"])


@frappe.whitelist()  # type: ignore[untyped-decorator]
def pay_invoice(
	invoice_name: str,
	amount: float | str,
	mode_of_payment: str = DEFAULT_MODE_OF_PAYMENT,
	reference_no: str = "",
	reference_date: str | None = None,
) -> dict[str, Any]:
	"""Create and submit a Payment Entry for a Sales Invoice (user clicked Pay).

	The user chooses the amount (full or partial) and the mode; nothing is
	created until this endpoint is called. A payment recorded here is still
	subject to the normal human ``payment_reviewer`` step.
	"""
	if not frappe.has_permission("Payment Entry", "create") or not frappe.has_permission(
		"Payment Entry", "submit"
	):
		frappe.throw(_("You do not have permission to create payments"), frappe.PermissionError)

	if not frappe.has_permission("Sales Invoice", "read", invoice_name):
		frappe.throw(_("You do not have permission to view this invoice"), frappe.PermissionError)

	invoice = frappe.get_doc("Sales Invoice", invoice_name)
	if invoice.docstatus != 1:
		frappe.throw(_("Only submitted invoices can be paid"))
	if invoice.is_return:
		frappe.throw(_("Credit notes are settled from the Return document, not from Pay"))
	if invoice.outstanding_amount <= 0:
		frappe.throw(_("Invoice {0} is already paid").format(invoice.name))

	outstanding = float(flt(invoice.outstanding_amount))
	amount_value = float(flt(amount))
	if amount_value <= 0 or amount_value > outstanding + 0.005:
		frappe.throw(_("Amount must be between 0 and {0}").format(outstanding))

	company_currency = frappe.get_cached_value("Company", invoice.company, "default_currency")
	if invoice.currency != company_currency:
		frappe.throw(_("Only company-currency invoices can be paid from the Desk Pay button"))

	mode_of_payment = (mode_of_payment or DEFAULT_MODE_OF_PAYMENT).strip()
	paid_from = frappe.get_cached_value("Company", invoice.company, "default_receivable_account")
	paid_to = _mode_account(mode_of_payment, invoice.company)
	posting_date = reference_date or today()

	payment = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": "Receive",
			"party_type": "Customer",
			"party": invoice.customer,
			"company": invoice.company,
			"posting_date": posting_date,
			"mode_of_payment": mode_of_payment,
			"paid_from": paid_from,
			"paid_to": paid_to,
			"paid_from_account_currency": company_currency,
			"paid_to_account_currency": company_currency,
			"paid_amount": amount_value,
			"received_amount": amount_value,
			"source_exchange_rate": 1,
			"target_exchange_rate": 1,
			"reference_no": reference_no or invoice.name,
			"reference_date": posting_date,
			"references": [
				{
					"reference_doctype": "Sales Invoice",
					"reference_name": invoice.name,
					"allocated_amount": amount_value,
				}
			],
		}
	)
	payment.insert(ignore_permissions=True)
	payment.submit()

	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "Sales Invoice",
			"reference_name": invoice.name,
			"content": _("Payment {0} created from the Desk Pay button by {1}").format(
				payment.name, frappe.session.user
			),
		}
	).insert(ignore_permissions=True)

	return {
		"payment_entry": payment.name,
		"amount": amount_value,
		"mode_of_payment": mode_of_payment,
	}


def _contact_links(like: str, doctype: str) -> list[str]:
	"""Party names whose linked Contact matches the phone fragment."""
	contacts = frappe.get_all(
		"Contact",
		or_filters=[["phone", "like", like], ["mobile_no", "like", like]],
		pluck="name",
		limit_page_length=20,
	)
	contacts += frappe.get_all(
		"Contact Phone",
		filters={"phone": ["like", like]},
		pluck="parent",
		limit_page_length=20,
	)
	if not contacts:
		return []
	names = frappe.get_all(
		"Dynamic Link",
		filters={
			"parent": ["in", list({*contacts})],
			"parenttype": "Contact",
			"link_doctype": doctype,
		},
		pluck="link_name",
		limit_page_length=20,
	)
	return [str(name) for name in names]


@frappe.whitelist()  # type: ignore[untyped-decorator]
def global_search(query: str) -> list[dict[str, str]]:
	"""Search Items (code/name/group/barcode), Customers and Suppliers
	(id/name/phone) and Sales Invoices (id).

	``frappe.get_list`` is used so the caller's permissions always apply.
	"""
	query = (query or "").strip()
	if len(query) < 2:
		return []
	like = f"%{query}%"
	results: list[dict[str, str]] = []
	seen: set[tuple[str, str]] = set()

	def add(doctype: str, name: str, title: str, subtitle: str = "") -> None:
		key = (doctype, name)
		if key in seen:
			return
		seen.add(key)
		results.append({"doctype": doctype, "name": name, "title": title, "subtitle": subtitle})

	item_filters = [
		["item_code", "like", like],
		["item_name", "like", like],
		["item_group", "like", like],
	]
	items = frappe.get_list(
		"Item",
		or_filters=item_filters,
		fields=["name", "item_code", "item_name", "item_group"],
		limit_page_length=8,
	)
	barcode_parents = frappe.get_all(
		"Item Barcode",
		filters={"barcode": ["like", like]},
		pluck="parent",
		limit_page_length=8,
	)
	barcode_parents += frappe.get_all(
		"Item",
		filters={"custom_barcode": ["like", like]},
		pluck="name",
		limit_page_length=8,
	)
	if barcode_parents:
		items += frappe.get_list(
			"Item",
			filters={"name": ["in", list({*barcode_parents})]},
			fields=["name", "item_code", "item_name", "item_group"],
			limit_page_length=8,
		)
	for item in items:
		add(
			"Item",
			item["name"],
			f"{item.get('item_code')} — {item.get('item_name')}",
			item.get("item_group") or "",
		)

	customer_names = _contact_links(like, "Customer")
	for customer in frappe.get_list(
		"Customer",
		or_filters=[
			["name", "like", like],
			["customer_name", "like", like],
			["mobile_no", "like", like],
		]
		+ ([["name", "in", customer_names]] if customer_names else []),
		fields=["name", "customer_name", "mobile_no"],
		limit_page_length=8,
	):
		add(
			"Customer",
			customer["name"],
			customer.get("customer_name") or customer["name"],
			customer.get("mobile_no") or customer["name"],
		)

	supplier_names = _contact_links(like, "Supplier")
	for supplier in frappe.get_list(
		"Supplier",
		or_filters=[
			["name", "like", like],
			["supplier_name", "like", like],
			["mobile_no", "like", like],
		]
		+ ([["name", "in", supplier_names]] if supplier_names else []),
		fields=["name", "supplier_name", "mobile_no"],
		limit_page_length=8,
	):
		add(
			"Supplier",
			supplier["name"],
			supplier.get("supplier_name") or supplier["name"],
			supplier.get("mobile_no") or supplier["name"],
		)

	for invoice in frappe.get_list(
		"Sales Invoice",
		or_filters=[["name", "like", like], ["customer_name", "like", like]],
		fields=["name", "customer_name", "grand_total", "status"],
		limit_page_length=8,
	):
		add(
			"Sales Invoice",
			invoice["name"],
			invoice["name"],
			f"{invoice.get('customer_name') or ''} · {invoice.get('status') or ''}",
		)

	return results[:30]


def awesomebar_search(txt: str) -> list[dict[str, Any]]:
	"""Hook for the Desk search bar (Ctrl+K): Items, parties and Sales Invoices.

	Ranking keeps invoices above items above parties, and the built-in search
	results (index 100) stay below all of them.
	"""
	index_by_doctype = {
		"Sales Invoice": 160,
		"Item": 150,
		"Customer": 140,
		"Supplier": 130,
	}
	results: list[dict[str, Any]] = []
	for row in global_search(txt):
		label = row["title"]
		if row["doctype"] != "Item" and row["subtitle"]:
			label = f"{row['title']} ({row['subtitle']})"
		results.append(
			{
				"label": label,
				"description": f"{_(row['doctype'])} · {row['name']}",
				"route": ["Form", row["doctype"], row["name"]],
				"index": index_by_doctype.get(row["doctype"], 120),
			}
		)
	return results[:20]


def auto_create_from_purchase_receipt(doc: Any, method: str | None = None) -> None:
	"""On Purchase Receipt submit, create the Purchase Invoice and transfer stock.

	DEC-86: the Purchase Receipt already updates stock; the Purchase Invoice is
	created from ERPNext's own mapping with ``update_stock = 0``. When an accepted
	warehouse is not ``Stores - DD`` (DEC-86), a submitted Material Transfer moves
	the received quantity there. A failure is logged and shown, never swallowed,
	and never rolls back the submitted Purchase Receipt.
	"""
	if frappe.flags.in_import or frappe.flags.in_patch or frappe.flags.in_install:
		return
	if not doc.items:
		return

	try:
		_create_purchase_invoice(doc)
	except Exception:
		frappe.log_error(
			title="Diva: auto Purchase Invoice from Purchase Receipt failed",
			message=frappe.get_traceback(),
		)
		frappe.msgprint(
			_(
				"Purchase Receipt {0} is saved, but the Purchase Invoice could not be created "
				"automatically. See Error Log."
			).format(doc.name),
			indicator="orange",
			alert=True,
		)

	try:
		_create_transfer(doc)
	except Exception:
		frappe.log_error(
			title="Diva: auto Stock Entry from Purchase Receipt failed",
			message=frappe.get_traceback(),
		)
		frappe.msgprint(
			_(
				"Purchase Receipt {0} is saved, but the transfer to {1} could not be created "
				"automatically. See Error Log."
			).format(doc.name, TARGET_WAREHOUSE),
			indicator="orange",
			alert=True,
		)


def _create_purchase_invoice(pr: Any) -> str | None:
	"""Create and submit the Purchase Invoice for this receipt, idempotently."""
	from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (  # type: ignore[import-not-found]
		make_purchase_invoice,
	)

	existing = frappe.get_all(
		"Purchase Invoice Item",
		filters={"purchase_receipt": pr.name, "docstatus": ["<", 2]},
		pluck="parent",
		limit_page_length=1,
	)
	if existing:
		return str(existing[0])

	invoice = make_purchase_invoice(pr.name)
	if invoice is None or not invoice.get("items"):
		return None

	invoice.set_posting_time = 1
	invoice.posting_date = pr.posting_date
	invoice.bill_no = pr.name
	invoice.bill_date = pr.posting_date
	invoice.update_stock = 0
	invoice.remarks = _("Created automatically from Purchase Receipt {0}").format(pr.name)
	invoice.insert(ignore_permissions=True)
	invoice.submit()
	return str(invoice.name)


def _create_transfer(pr: Any) -> str | None:
	"""Move every received line from its accepted warehouse to Stores - DD."""
	existing = frappe.db.exists(
		"Stock Entry",
		{"purchase_receipt_no": pr.name, "docstatus": ["<", 2]},
	)
	if existing:
		return str(existing)

	rows = []
	for item in pr.items:
		source = item.warehouse or pr.set_warehouse or TARGET_WAREHOUSE
		if source == TARGET_WAREHOUSE:
			continue
		rows.append(
			{
				"item_code": item.item_code,
				"item_name": item.item_name,
				"qty": item.qty,
				"uom": item.stock_uom or item.uom,
				"stock_uom": item.stock_uom or item.uom,
				"conversion_factor": 1,
				"s_warehouse": source,
				"t_warehouse": TARGET_WAREHOUSE,
				"batch_no": item.batch_no,
				"serial_no": item.serial_no,
				"cost_center": item.cost_center,
			}
		)
	if not rows:
		return None

	entry = frappe.new_doc("Stock Entry")
	entry.stock_entry_type = "Material Transfer"
	entry.company = pr.company
	entry.posting_date = pr.posting_date
	entry.set_posting_time = 1
	entry.purchase_receipt_no = pr.name
	entry.from_warehouse = rows[0]["s_warehouse"]
	entry.to_warehouse = TARGET_WAREHOUSE
	entry.remarks = _("Automatic transfer to {0} for Purchase Receipt {1}").format(TARGET_WAREHOUSE, pr.name)
	for row in rows:
		entry.append("items", row)
	entry.insert(ignore_permissions=True)
	entry.submit()
	return str(entry.name)
