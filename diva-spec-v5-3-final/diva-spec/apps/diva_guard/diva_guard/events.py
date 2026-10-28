"""Server-side enforcement of the Diva counter rules (DEC-30, TASK-E-14a).

The rules themselves come from ``packages/rules-engine``; this module only maps
ERPNext documents onto them. Nothing here may be bypassed from the browser:
validation runs on the server for every Sales Invoice, whether it comes from
POS Next, the desk or an API client.
"""

import hashlib
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime
from rules_engine import PCS_PER_DOZEN, quantize_money, to_decimal, validate_discount, validate_moq

MANAGER_ROLES = {"Sales Manager", "Sales Master Manager", "System Manager"}
OVERRIDE_HEADER = "X-Diva-Override-Token"


def _setting(name: str, default: object = None) -> object:
	value = frappe.db.get_single_value("Diva Guard Settings", name)
	return default if value is None else value


def _user_roles(user: str) -> set[str]:
	return set(frappe.get_roles(user))


def _is_manager(user: str) -> bool:
	return bool(MANAGER_ROLES & _user_roles(user))


def _product_rule(item_code: str):
	return frappe.db.get_value(
		"Diva Product Rule",
		{"item": item_code, "is_active": 1},
		["moq_dozen", "step_dozen", "max_discount_pct"],
		as_dict=True,
	)


def _dec(value: object) -> Decimal:
	return to_decimal(str(value or 0))


def _qty_dozens(item) -> Decimal:
	return _dec(item.stock_qty) / Decimal(PCS_PER_DOZEN)


def _check_counter_payment(doc) -> None:
	paid = sum(
		(_dec(payment.amount) for payment in doc.payments or []),
		Decimal("0"),
	)
	due = _dec(doc.rounded_total or doc.grand_total)
	if paid < due:
		frappe.throw(
			_(
				"Counter sales must be paid in full: paid {0}, due {1}. "
				"Partial payment and credit are not allowed at the counter."
			).format(paid, due),
			frappe.ValidationError,
		)


def _check_moq(doc) -> None:
	for item in doc.items:
		rule = _product_rule(item.item_code)
		if not rule:
			continue
		violations = validate_moq(_qty_dozens(item), str(rule.moq_dozen or 0), str(rule.step_dozen or 0))
		if violations:
			frappe.throw(
				_("Minimum quantity for {0} is {1} Dozen in steps of {2} Dozen (current {3} Dozen).").format(
					item.item_code,
					rule.moq_dozen or 0,
					rule.step_dozen or 0,
					_qty_dozens(item),
				),
				frappe.ValidationError,
			)


def _check_stock(doc) -> None:
	for item in doc.items:
		if not item.warehouse:
			continue
		is_stock_item = frappe.db.get_value("Item", item.item_code, "is_stock_item")
		if not is_stock_item:
			continue
		bin_row = frappe.db.get_value(
			"Bin",
			{"item_code": item.item_code, "warehouse": item.warehouse},
			["actual_qty", "reserved_qty"],
			as_dict=True,
		)
		# No Bin means nothing was ever received there: zero available, not a skip.
		available = _dec(bin_row.actual_qty) - _dec(bin_row.reserved_qty) if bin_row else Decimal("0")
		if available < _dec(item.stock_qty):
			frappe.throw(
				_("Not enough available stock for {0} in {1}: available {2}, requested {3}.").format(
					item.item_code,
					item.warehouse,
					available,
					item.stock_qty,
				),
				frappe.ValidationError,
			)


def _price_list_rate(doc, item) -> Decimal:
	"""Authoritative rate from Item Price, never the client-supplied rate.

	Item Price rows are usually per Dozen. For a Nos line we convert the Dozen
	price down (1 Dozen = 12 Nos) so a missing Nos row cannot become an
	arbitrary client price.
	"""
	rows = frappe.get_all(
		"Item Price",
		filters={"item_code": item.item_code, "price_list": doc.selling_price_list},
		fields=["uom", "price_list_rate"],
		limit=0,
	)
	if not rows:
		frappe.throw(
			_("No selling price is configured for {0} in {1}.").format(
				item.item_code, doc.selling_price_list
			),
			frappe.ValidationError,
		)
	exact = next((row for row in rows if row.uom == item.uom), None)
	if exact:
		return _dec(exact.price_list_rate)
	stock_uom = frappe.db.get_value("Item", item.item_code, "stock_uom")
	source = next((row for row in rows if row.uom == "Dozen"), None)
	if source is None:
		source = next((row for row in rows if row.uom == stock_uom), rows[0])
	source_factor = _dec(
		frappe.db.get_value(
			"UOM Conversion Detail",
			{"parent": item.item_code, "uom": source.uom},
			"conversion_factor",
		)
	) or Decimal("1")
	line_factor = _dec(item.conversion_factor) or Decimal("1")
	return _dec(source.price_list_rate) / source_factor * line_factor


def _invoice_discount(doc) -> tuple[Decimal, Decimal]:
	"""Return (price-list subtotal, net subtotal after all discounts)."""
	price_total = Decimal("0")
	for item in doc.items:
		price_total += _price_list_rate(doc, item) * _dec(item.qty)
	net_total = _dec(doc.net_total) - _dec(doc.discount_amount)
	return price_total, net_total


def _consume_override(doc, discount_percent: Decimal, amount: Decimal) -> bool:
	token = frappe.get_request_header(OVERRIDE_HEADER)
	if not token:
		return False
	token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
	lock = frappe.cache.lock(f"diva_guard:override:{token_hash}", timeout=10)
	if not lock.acquire(blocking=False):
		return False
	try:
		rows = frappe.db.sql(
			"""
            SELECT name, user, voucher_name, discount_percent, amount, expires_at,
                   status, used
            FROM `tabDiva Override Approval`
            WHERE token_hash=%s
            """,
			(token_hash,),
			as_dict=True,
		)
		approval = rows[0] if rows else None
		if not approval:
			return False
		if approval.user != frappe.session.user:
			return False
		if approval.status == "Used" and approval.voucher_name == doc.name:
			return True
		if approval.status != "Pending" or approval.used:
			return False
		if approval.voucher_name and approval.voucher_name != doc.name:
			return False
		if get_datetime(approval.expires_at) < now_datetime():
			frappe.db.set_value("Diva Override Approval", approval.name, "status", "Expired")
			return False
		if _dec(approval.discount_percent) + Decimal("0.01") < discount_percent:
			return False
		if _dec(approval.amount) + Decimal("0.01") < amount:
			return False
		frappe.db.set_value(
			"Diva Override Approval",
			approval.name,
			{
				"status": "Used",
				"used": 1,
				"voucher_doctype": doc.doctype,
				"voucher_name": doc.name,
			},
		)
		return True
	finally:
		lock.release()


def _check_pos_price_list(doc) -> None:
	if not doc.get("is_pos"):
		return
	if not doc.get("pos_profile"):
		frappe.throw(_("A POS sale must have a POS profile."), frappe.ValidationError)
	expected = frappe.db.get_value("POS Profile", doc.pos_profile, "selling_price_list")
	if expected and doc.selling_price_list != expected:
		frappe.throw(
			_("This POS profile must use the {0} price list.").format(expected),
			frappe.ValidationError,
		)


def _check_discount(doc, consume: bool = True) -> None:
	cashier_limit = _dec(_setting("discount_cashier_limit_pct", 5))
	manager_limit = _dec(_setting("discount_manager_limit_pct", 15))
	for item in doc.items:
		rule = _product_rule(item.item_code)
		if rule and rule.max_discount_pct:
			manager_limit = min(manager_limit, _dec(rule.max_discount_pct))
		list_rate = _price_list_rate(doc, item)
		if list_rate > 0 and _dec(item.rate) > list_rate:
			frappe.throw(
				_("Rate for {0} is above the price list ({1} > {2}).").format(
					item.item_code, item.rate, list_rate
				),
				frappe.ValidationError,
			)
	price_total, net_total = _invoice_discount(doc)
	if price_total <= 0:
		return
	result = validate_discount(price_total, net_total, cashier_limit, manager_limit)
	if result["violations"]:
		frappe.throw(
			_("Discount {0}% exceeds the manager limit of {1}%.").format(
				result["discount_percent"], manager_limit
			),
			frappe.ValidationError,
		)
	if not result["requires_manager"]:
		return
	if _is_manager(frappe.session.user):
		return
	if not consume:
		# Draft saves may wait for a manager; submit enforces the approval.
		return
	discount = to_decimal(str(result["discount_percent"]))
	if _consume_override(doc, discount, price_total - net_total):
		return
	frappe.throw(
		_("Discount {0}% is above the cashier limit of {1}%: a manager PIN approval is required.").format(
			discount, cashier_limit
		),
		frappe.PermissionError,
	)


def validate_sales_invoice(doc, method: str | None = None) -> None:
	if getattr(doc.flags, "ignore_diva_guard", False):
		return
	if not _setting("enabled", 1):
		return
	if doc.get("is_return"):
		return
	is_manager = _is_manager(frappe.session.user)
	for item in doc.items:
		if _dec(item.qty) <= 0 or _dec(item.stock_qty) <= 0:
			frappe.throw(
				_("Line {0} must have a positive quantity.").format(item.idx),
				frappe.ValidationError,
			)
		if (_dec(item.rate) <= 0 or item.get("is_free_item")) and not is_manager:
			frappe.throw(
				_("Free items need manager approval (line {0}).").format(item.idx),
				frappe.PermissionError,
			)
	if _setting("block_counter_credit", 1) and (doc.get("is_pos") or not is_manager):
		_check_counter_payment(doc)
	if _setting("enforce_moq", 1):
		_check_moq(doc)
	if _setting("enforce_price_list", 1):
		_check_pos_price_list(doc)
		_check_discount(doc, consume=method == "before_submit" or doc.docstatus == 1)
	if _setting("enforce_reserved_stock", 1):
		_check_stock(doc)


def _sync_standard_selling_price(doc) -> None:
	"""Keep the Standard Selling prices in step with the quick-entry rate.

	The quick-entry field is per Dozen. ERPNext's Item.after_insert creates a
	stock-UOM price from standard_rate; convert that one to a per-piece rate and
	keep an explicit Dozen row.
	"""
	rate = _dec(doc.get("standard_rate"))
	if rate <= 0:
		return
	if not any(str(row.uom) == "Dozen" for row in doc.get("uoms") or []):
		doc.append("uoms", {"uom": "Dozen", "conversion_factor": PCS_PER_DOZEN})
	if not frappe.db.exists("Price List", "Standard Selling"):
		return
	rows = frappe.get_all(
		"Item Price",
		filters={"item_code": doc.name, "price_list": "Standard Selling"},
		fields=["name", "uom"],
		limit=0,
	)
	dozen = next((row for row in rows if str(row.uom) == "Dozen"), None)
	stock = next((row for row in rows if str(row.uom) == str(doc.stock_uom)), None)
	if dozen:
		frappe.db.set_value("Item Price", dozen.name, "price_list_rate", rate, update_modified=False)
	else:
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": doc.name,
				"price_list": "Standard Selling",
				"uom": "Dozen",
				"price_list_rate": rate,
				"selling": 1,
			}
		).insert(ignore_permissions=True)
	if str(doc.stock_uom) != "Dozen":
		stock_rate = quantize_money(rate / Decimal(PCS_PER_DOZEN))
		if stock:
			frappe.db.set_value(
				"Item Price", stock.name, "price_list_rate", stock_rate, update_modified=False
			)
		else:
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"item_code": doc.name,
					"price_list": "Standard Selling",
					"uom": doc.stock_uom,
					"price_list_rate": stock_rate,
					"selling": 1,
				}
			).insert(ignore_permissions=True)


def apply_quick_barcode(doc, method: str | None = None) -> None:
	"""Copy the one-field quick-entry barcode and price (DEC-78/79)."""
	if getattr(doc.flags, "ignore_diva_guard", False):
		return
	if _dec(doc.get("opening_stock")) > 0 and not _dec(doc.get("valuation_rate")):
		selling = _dec(doc.get("standard_rate"))
		if selling > 0:
			doc.valuation_rate = quantize_money(selling / Decimal(PCS_PER_DOZEN))
	if _dec(doc.get("standard_rate")) > 0 and not any(
		str(row.uom) == "Dozen" for row in doc.get("uoms") or []
	):
		doc.append("uoms", {"uom": "Dozen", "conversion_factor": PCS_PER_DOZEN})
	if not doc.meta.has_field("custom_barcode"):
		return
	value = str(doc.get("custom_barcode") or "").strip()
	if not value:
		return
	owner = frappe.db.get_value("Item Barcode", {"barcode": value}, "parent")
	if owner and owner != doc.name:
		frappe.throw(
			_("Barcode {0} is already used by item {1}.").format(value, owner),
			frappe.ValidationError,
		)
	if not any(str(row.barcode or "").strip() == value for row in doc.get("barcodes") or []):
		doc.append(
			"barcodes",
			{
				"barcode": value,
				"uom": doc.get("stock_uom") or "Nos",
			},
		)
	doc.set("custom_barcode", None)


def sync_quick_price(doc, method: str | None = None) -> None:
	"""Sync the quick-entry selling rate after the Item exists (DEC-79)."""
	if getattr(doc.flags, "ignore_diva_guard", False):
		return
	if method == "on_update" and not doc.has_value_changed("standard_rate"):
		# Do not clobber a deliberate Item Price edit on an unrelated Item save.
		return
	_sync_standard_selling_price(doc)
