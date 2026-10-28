"""Manager PIN approvals for discounts and price overrides (TASK-E-14a).

The PIN itself is never stored in the repository or returned by the API. Only a
PBKDF2-HMAC-SHA256 hash and its salt are stored in Diva Guard Settings; the PIN
is read from the environment when the site is seeded/rotated.
"""

import hashlib
import hmac
import re
import secrets

import frappe
from frappe import _
from frappe.utils import add_to_date, now_datetime

PIN_ITERATIONS = 260000
MAX_ATTEMPTS = 5
ATTEMPT_WINDOW_SECONDS = 300


def hash_pin(pin: str, salt_hex: str, iterations: int = PIN_ITERATIONS) -> str:
	safe_iterations = max(int(iterations or PIN_ITERATIONS), PIN_ITERATIONS)
	return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), bytes.fromhex(salt_hex), safe_iterations).hex()


def _attempts_key() -> str:
	return f"diva_guard:pin_attempts:{frappe.session.user}"


def _too_many_attempts() -> bool:
	attempts = int(frappe.cache.get(_attempts_key()) or 0)
	return attempts >= MAX_ATTEMPTS


def _record_failure() -> None:
	key = _attempts_key()
	attempts = int(frappe.cache.get(key) or 0) + 1
	frappe.cache.set(key, attempts, ex=ATTEMPT_WINDOW_SECONDS)


def _verify_pin(pin: str) -> None:
	settings = frappe.get_single("Diva Guard Settings")
	if not settings.manager_pin_hash or not settings.manager_pin_salt:
		frappe.throw(
			_("Manager PIN is not configured. Set it with the Diva Guard seed script."),
			frappe.PermissionError,
		)
	try:
		bytes.fromhex(settings.manager_pin_salt)
	except ValueError:
		frappe.throw(
			_("Manager PIN salt is malformed; re-run the Diva Guard seed script."),
			frappe.PermissionError,
		)
	if _too_many_attempts():
		frappe.throw(
			_("Too many PIN attempts. Try again in a few minutes."),
			frappe.PermissionError,
		)
	actual = hash_pin(
		str(pin), settings.manager_pin_salt, int(settings.manager_pin_iterations or PIN_ITERATIONS)
	)
	if not hmac.compare_digest(actual, settings.manager_pin_hash):
		_record_failure()
		frappe.throw(_("Invalid manager PIN."), frappe.PermissionError)
	frappe.cache.delete(_attempts_key())


@frappe.whitelist()
def approve_discount(
	pin: str,
	reason: str,
	discount_percent: float,
	amount: float,
	voucher_doctype: str = "Sales Invoice",
	voucher_name: str | None = None,
) -> dict[str, str]:
	"""Verify the manager PIN and issue a short-lived, single-use approval token."""
	if len(str(pin)) < 6:
		frappe.throw(_("The manager PIN must be at least 6 characters."), frappe.PermissionError)
	if voucher_doctype != "Sales Invoice":
		frappe.throw(_("Only Sales Invoice approvals are supported."), frappe.ValidationError)
	_verify_pin(pin)
	token = secrets.token_urlsafe(24)
	token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
	expires_at = add_to_date(now_datetime(), minutes=10)
	approval = frappe.get_doc(
		{
			"doctype": "Diva Override Approval",
			"token_hash": token_hash,
			"user": frappe.session.user,
			"voucher_doctype": voucher_doctype,
			"voucher_name": voucher_name,
			"discount_percent": discount_percent,
			"amount": amount,
			"reason": reason,
			"approved_by": "Administrator",
			"approval_method": "Manager PIN",
			"expires_at": expires_at,
			"status": "Pending",
		}
	)
	approval.insert(ignore_permissions=True)
	return {"token": token, "expires_at": str(expires_at), "name": approval.name}


@frappe.whitelist()
def qr_svg(text: str) -> str:
	"""Return an inline SVG QR code for print formats (no external service)."""
	import io

	import pyqrcode

	code = pyqrcode.create(str(text)[:900], error="M", encoding="utf-8")
	buffer = io.BytesIO()
	code.svg(buffer, scale=3, quiet_zone=2)
	svg = buffer.getvalue().decode("utf-8")
	width_match = re.search(r'width="(\d+)"', svg)
	height_match = re.search(r'height="(\d+)"', svg)
	if width_match and height_match:
		width, height = width_match.group(1), height_match.group(1)
		svg = svg.replace(
			'class="pyqrcode">',
			f'class="pyqrcode" viewBox="0 0 {width} {height}" shape-rendering="crispEdges">',
			1,
		)
	return svg
