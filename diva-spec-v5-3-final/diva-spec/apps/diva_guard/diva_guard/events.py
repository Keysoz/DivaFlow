"""Server-side enforcement of the Diva counter rules (DEC-30, TASK-E-14a).

The rules themselves come from ``packages/rules-engine``; this module only maps
ERPNext documents onto them. Nothing here may be bypassed from the browser:
validation runs on the server for every Sales Invoice, whether it comes from
POS Next, the desk or an API client.
"""

from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime
from rules_engine import PCS_PER_DOZEN, to_decimal, validate_discount, validate_moq

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
		bin_row = frappe.db.get_value(
			"Bin",
			{"item_code": item.item_code, "warehouse": item.warehouse},
			["actual_qty", "reserved_qty"],
			as_dict=True,
		)
		if not bin_row:
			continue
		available = _dec(bin_row.actual_qty) - _dec(bin_row.reserved_qty)
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
	"""Authoritative rate from Item Price, never the client-supplied value."""
	rate = frappe.db.get_value(
		"Item Price",
		{
			"item_code": item.item_code,
			"price_list": doc.selling_price_list,
			"uom": item.uom,
		},
		"price_list_rate",
	)
	if rate:
		return _dec(rate)
	return _dec(item.price_list_rate)


def _invoice_discount(doc) -> tuple[Decimal, Decimal]:
	"""Return (price-list subtotal, net subtotal after all discounts)."""
	price_total = Decimal("0")
	for item in doc.items:
		price_total += _price_list_rate(doc, item) * _dec(item.qty)
	net_total = _dec(doc.net_total) - _dec(doc.discount_amount)
	return price_total, net_total


def _consume_override(doc, discount_percent: Decimal, amount: Decimal) -> bool:
	request = getattr(frappe.local, "request", None)
	token = request.headers.get(OVERRIDE_HEADER) if request else None
	if not token:
		return False
	approval = frappe.db.get_value(
		"Diva Override Approval",
		{"token": token, "status": "Pending", "used": 0},
		["name", "user", "discount_percent", "amount", "expires_at"],
		as_dict=True,
	)
	if not approval:
		return False
	if approval.user != frappe.session.user:
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


def _check_pos_price_list(doc) -> None:
	if not doc.get("is_pos") or not doc.get("pos_profile"):
		return
	expected = frappe.db.get_value("POS Profile", doc.pos_profile, "selling_price_list")
	if expected and doc.selling_price_list != expected:
		frappe.throw(
			_("This POS profile must use the {0} price list.").format(expected),
			frappe.ValidationError,
		)


def _check_discount(doc) -> None:
	cashier_limit = _dec(_setting("discount_cashier_limit_pct", 5))
	manager_limit = _dec(_setting("discount_manager_limit_pct", 15))
	for item in doc.items:
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
	if _setting("block_counter_credit", 1) and (doc.get("is_pos") or not _is_manager(frappe.session.user)):
		_check_counter_payment(doc)
	if _setting("enforce_moq", 1):
		_check_moq(doc)
	if _setting("enforce_price_list", 1):
		_check_pos_price_list(doc)
		_check_discount(doc)
	if _setting("enforce_reserved_stock", 1):
		_check_stock(doc)
