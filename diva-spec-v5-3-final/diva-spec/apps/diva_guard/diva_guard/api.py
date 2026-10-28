"""Manager PIN approvals for discounts and price overrides (TASK-E-14a).

The PIN itself is never stored in the repository or returned by the API. Only a
PBKDF2-HMAC-SHA256 hash and its salt are stored in Diva Guard Settings; the PIN
is read from the environment when the site is seeded/rotated.
"""

import hashlib
import hmac
import secrets

import frappe
from frappe import _
from frappe.utils import add_to_date, now_datetime

PIN_ITERATIONS = 260000
MAX_ATTEMPTS = 5
ATTEMPT_WINDOW_SECONDS = 300


def hash_pin(pin: str, salt_hex: str, iterations: int = PIN_ITERATIONS) -> str:
	return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), bytes.fromhex(salt_hex), iterations).hex()


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
	_verify_pin(pin)
	token = secrets.token_urlsafe(24)
	expires_at = add_to_date(now_datetime(), minutes=10)
	approval = frappe.get_doc(
		{
			"doctype": "Diva Override Approval",
			"token": token,
			"user": frappe.session.user,
			"voucher_doctype": voucher_doctype,
			"voucher_name": voucher_name,
			"discount_percent": discount_percent,
			"amount": amount,
			"reason": reason,
			"approved_by": "Administrator",
			"expires_at": expires_at,
			"status": "Pending",
		}
	)
	approval.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"token": token, "expires_at": str(expires_at)}
