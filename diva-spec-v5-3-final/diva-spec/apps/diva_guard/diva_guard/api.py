"""Manager PIN approvals for discounts and price overrides (TASK-E-14a).

The PIN itself is never stored in the repository or returned by the API. Only a
PBKDF2-HMAC-SHA256 hash and its salt are stored in Diva Guard Settings; the PIN
is read from the environment when the site is seeded/rotated.

PROD-19..PROD-26: the same module carries the company profile endpoints and the
one-time setup token used by the first-run wizard. Every write here is a data
change only; no core code is modified.
"""

import base64
import binascii
import hashlib
import hmac
import json
import re
import secrets

import frappe
from frappe import _
from frappe.utils import add_to_date, get_fullname, now_datetime, validate_email_address

PIN_ITERATIONS = 260000
MAX_ATTEMPTS = 5
ATTEMPT_WINDOW_SECONDS = 300

SETUP_TOKEN_CACHE_KEY = "diva_guard:setup_token_hash"
SETUP_TOKEN_TTL_SECONDS = 3600
SETUP_ROLES = frozenset({"System Manager"})

MAX_LOGO_BYTES = 2 * 1024 * 1024
LOGO_SIGNATURES = ((b"\x89PNG\r\n\x1a\n", "png"), (b"\xff\xd8\xff", "jpg"))
ABBR_PATTERN = re.compile(r"^[A-Z0-9]{1,8}$")

# A company that owns any submitted document is frozen for name and abbreviation.
TRANSACTION_DOCTYPES = (
	"Sales Invoice",
	"Purchase Invoice",
	"Delivery Note",
	"Purchase Receipt",
	"Stock Entry",
	"Payment Entry",
	"Journal Entry",
	"GL Entry",
)

PROFILE_TEXT_FIELDS = {
	"phone": "phone_no",
	"email": "email",
	"website": "website",
	"tax_id": "tax_id",
	"description": "company_description",
}


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
	"""Return an inline SVG QR code for API clients (print formats use the Jinja method)."""
	from diva_guard.jinja_methods import qr_svg as render_qr

	return render_qr(text)


@frappe.whitelist()
def verify_manager_pin(pin: str) -> dict[str, str]:
	"""Check the manager PIN without issuing a discount approval."""
	_verify_pin(pin)
	return {"status": "ok"}


# --- Company profile (PROD-19) -------------------------------------------------


def _require_system_manager() -> None:
	if frappe.session.user in (None, "Guest"):
		frappe.throw(_("Please sign in first."), frappe.PermissionError)
	if not SETUP_ROLES.intersection(frappe.get_roles()):
		frappe.throw(_("Only a System Manager can change the company profile."), frappe.PermissionError)


def _default_company() -> str:
	name = frappe.db.get_single_value("Global Defaults", "default_company")
	if not name:
		frappe.throw(
			_("No default company is configured. Finish the setup wizard first."),
			frappe.ValidationError,
		)
	return str(name)


def _has_transactions(company: str) -> bool:
	for doctype in TRANSACTION_DOCTYPES:
		if frappe.db.exists(doctype, {"company": company, "docstatus": 1}):
			return True
	return False


def _abbr_locked(company: str) -> bool:
	"""The abbreviation names every warehouse, so it is locked once one exists."""
	return bool(frappe.db.exists("Warehouse", {"company": company}))


def _billing_address_name(company: str) -> str | None:
	candidates = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Address", "link_doctype": "Company", "link_name": company},
		pluck="parent",
	)
	if not candidates:
		return None
	primary = frappe.get_all(
		"Address",
		filters={"name": ["in", candidates], "is_primary_address": 1, "address_type": "Billing"},
		pluck="name",
	)
	return (primary or candidates)[0]


def _as_dict(value: str | dict | None, label: str) -> dict:
	if value is None:
		return {}
	if isinstance(value, dict):
		return value
	try:
		parsed = json.loads(value)
	except (TypeError, ValueError):
		frappe.throw(_("{0} must be a JSON object.").format(label), frappe.ValidationError)
	if not isinstance(parsed, dict):
		frappe.throw(_("{0} must be a JSON object.").format(label), frappe.ValidationError)
	return parsed


def _empty_profile() -> dict:
	"""A fresh site has no Company yet; the wizard creates it."""
	return {
		"name": "",
		"company_name": "",
		"abbr": "",
		"logo": None,
		"phone": "",
		"email": "",
		"website": "",
		"tax_id": "",
		"description": "",
		"country": "Egypt",
		"currency": "EGP",
		"address": None,
		"can_change_name": True,
		"can_change_abbr": True,
		"setup_complete": _setup_complete(),
	}


@frappe.whitelist()
def get_company_profile() -> dict:
	"""Return the editable company profile for the wizard and the profile screen."""
	_require_system_manager()
	name = frappe.db.get_single_value("Global Defaults", "default_company")
	if not name or not frappe.db.exists("Company", str(name)):
		return _empty_profile()
	company = frappe.get_doc("Company", str(name))
	address_name = _billing_address_name(company.name)
	address = frappe.get_doc("Address", address_name) if address_name else None
	has_transactions = _has_transactions(company.name)
	return {
		"name": company.name,
		"company_name": company.company_name,
		"abbr": company.abbr,
		"logo": company.company_logo or None,
		"phone": company.phone_no or "",
		"email": company.email or "",
		"website": company.website or "",
		"tax_id": company.tax_id or "",
		"description": company.company_description or "",
		"country": company.country or "",
		"currency": company.default_currency or "",
		"address": {
			"address_line1": address.address_line1 or "",
			"address_line2": address.address_line2 or "",
			"city": address.city or "",
			"country": address.country or "",
		}
		if address
		else None,
		"can_change_name": not has_transactions,
		"can_change_abbr": not has_transactions and not _abbr_locked(company.name),
		"setup_complete": _setup_complete(),
	}


def _decode_logo(data_uri: str) -> tuple[bytes, str]:
	"""Return (content, extension) for a base64 data URI, checked by magic bytes."""
	if not isinstance(data_uri, str) or not data_uri.startswith("data:") or ";base64" not in data_uri:
		frappe.throw(_("The logo must be a base64 PNG or JPEG image."), frappe.ValidationError)
	payload = data_uri.split(",", 1)[1] if "," in data_uri else ""
	try:
		content = base64.b64decode(payload, validate=True)
	except (binascii.Error, ValueError):
		frappe.throw(_("The logo could not be decoded."), frappe.ValidationError)
	if not content:
		frappe.throw(_("The logo file is empty."), frappe.ValidationError)
	if len(content) > MAX_LOGO_BYTES:
		frappe.throw(_("The logo must be smaller than 2 MB."), frappe.ValidationError)
	for signature, extension in LOGO_SIGNATURES:
		if content.startswith(signature):
			return content, extension
	frappe.throw(_("The logo must be a PNG or JPEG image."), frappe.ValidationError)
	raise AssertionError("unreachable")


def _attach_logo(company: str, content: bytes, extension: str) -> str:
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"company-logo.{extension}",
			"attached_to_doctype": "Company",
			"attached_to_name": company,
			"is_private": 0,
			"content": content,
		}
	)
	file_doc.insert(ignore_permissions=True)
	return file_doc.file_url


def _save_billing_address(company: frappe.Document, payload: dict) -> None:
	address_name = _billing_address_name(company.name)
	address = frappe.get_doc("Address", address_name) if address_name else frappe.new_doc("Address")
	if not address_name:
		address.address_type = "Billing"
		address.is_primary_address = 1
		address.append("links", {"link_doctype": "Company", "link_name": company.name})
	for field in ("address_line1", "address_line2", "city", "country"):
		if field in payload:
			setattr(address, field, payload[field])
	address.save()


@frappe.whitelist()
def update_company_profile(profile_data: str | dict | None = None) -> dict[str, str]:
	"""Update the company profile."""
	_require_system_manager()
	return _apply_company_profile(_as_dict(profile_data, _("Company profile")))


def _company_to_edit(payload: dict) -> frappe.Document:
	"""Return the site's company, creating it on a fresh site.

	ERPNext derives the chart of accounts and the default warehouse names from
	the abbreviation at Company creation, so the wizard must create the Company
	instead of renaming one that was seeded earlier.
	"""
	name = frappe.db.get_single_value("Global Defaults", "default_company")
	if name and frappe.db.exists("Company", str(name)):
		return frappe.get_doc("Company", str(name))

	company_name = str(payload.get("company_name") or "").strip()
	abbr = str(payload.get("abbr") or "").strip().upper()
	if not company_name:
		frappe.throw(_("Company Name is required."), frappe.ValidationError)
	if not ABBR_PATTERN.match(abbr):
		frappe.throw(
			_("The abbreviation must be 1 to 8 uppercase letters or digits."),
			frappe.ValidationError,
		)
	address = payload.get("address") if isinstance(payload.get("address"), dict) else {}
	country = str(payload.get("country") or (address or {}).get("country") or "Egypt")
	# A bare site lacks ERPNext's setup fixtures and language defaults; the
	# standard setup wizard normally installs them before creating the Company.
	from diva_guard.setup import ensure_erpnext_fixtures, ensure_site_defaults

	ensure_site_defaults()
	ensure_erpnext_fixtures()
	company = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": company_name,
			"abbr": abbr,
			"country": country,
			"default_currency": str(payload.get("currency") or "EGP"),
			"create_chart_of_accounts_based_on": "Standard Template",
			"chart_of_accounts": "Standard",
		}
	).insert()
	frappe.db.set_single_value("Global Defaults", "default_company", company.name)
	return company


def _apply_company_profile(payload: dict) -> dict[str, str]:
	"""Write the profile fields.

	The name and abbreviation freeze once the company owns a submitted document.
	The abbreviation additionally freezes once a warehouse exists, because
	warehouse names embed it. Everything else stays editable forever.
	"""
	company = _company_to_edit(payload)
	has_transactions = _has_transactions(company.name)

	new_name = str(payload.get("company_name") or "").strip()
	if new_name and new_name != company.company_name:
		if has_transactions:
			frappe.throw(
				_("The company name cannot change after the first transaction."),
				frappe.ValidationError,
			)
		company.company_name = new_name

	new_abbr = str(payload.get("abbr") or "").strip().upper()
	if new_abbr and new_abbr != company.abbr:
		if has_transactions:
			frappe.throw(
				_("The company abbreviation cannot change after the first transaction."),
				frappe.ValidationError,
			)
		if _abbr_locked(company.name):
			frappe.throw(
				_("The abbreviation cannot change because warehouses already use it."),
				frappe.ValidationError,
			)
		if not ABBR_PATTERN.match(new_abbr):
			frappe.throw(
				_("The abbreviation must be 1 to 8 uppercase letters or digits."),
				frappe.ValidationError,
			)
		company.abbr = new_abbr

	for key, fieldname in PROFILE_TEXT_FIELDS.items():
		if key not in payload:
			continue
		value = str(payload.get(key) or "").strip()
		if fieldname == "email" and value:
			validate_email_address(value, throw=True)
		setattr(company, fieldname, value)

	logo = payload.get("logo")
	if logo:
		content, extension = _decode_logo(str(logo))
		company.company_logo = _attach_logo(company.name, content, extension)
		# DEC-95: the Desk navbar reads app_logo, which must be the public copy.
		frappe.db.set_single_value("Navbar Settings", "app_logo", company.company_logo)

	address_payload = payload.get("address")
	if isinstance(address_payload, dict):
		_save_billing_address(company, address_payload)

	company.save()
	return {
		"status": "ok",
		"name": company.name,
		"company_name": company.company_name,
		"abbr": company.abbr,
	}


# --- First-run setup token (PROD-23, PROD-26) ----------------------------------


def _setup_complete() -> bool:
	return bool(frappe.db.get_single_value("System Settings", "setup_complete"))


def _token_digest(token: str) -> str:
	return hashlib.sha256(str(token).encode("utf-8")).hexdigest()


def _audit(subject: str) -> None:
	# Activity Log.operation only allows Login/Logout/Impersonate, so the action
	# is carried by the subject and the status stays Success.
	frappe.get_doc(
		{
			"doctype": "Activity Log",
			"subject": subject,
			"user": frappe.session.user,
			"full_name": get_fullname(frappe.session.user),
			"status": "Success",
		}
	).insert(ignore_permissions=True)


@frappe.whitelist()
def get_setup_token() -> dict:
	"""Issue a short-lived, single-use token for the first-run wizard."""
	_require_system_manager()
	if _setup_complete():
		frappe.throw(_("Setup is already complete."), frappe.PermissionError)
	token = secrets.token_urlsafe(32)
	frappe.cache.set_value(
		SETUP_TOKEN_CACHE_KEY,
		_token_digest(token),
		expires_in_sec=SETUP_TOKEN_TTL_SECONDS,
	)
	return {"token": token, "expires_in_seconds": SETUP_TOKEN_TTL_SECONDS}


@frappe.whitelist()
def verify_setup_token(token: str) -> dict:
	"""Check the setup token without consuming it."""
	_require_system_manager()
	stored = frappe.cache.get_value(SETUP_TOKEN_CACHE_KEY)
	if not stored or not hmac.compare_digest(str(stored), _token_digest(token)):
		frappe.throw(
			_("The setup token is invalid or has expired."),
			frappe.PermissionError,
		)
	return {"status": "ok"}


@frappe.whitelist()
def complete_setup(token: str, profile_data: str | dict | None = None) -> dict:
	"""Consume the setup token, save the profile, and start the configuration.

	The token is verified before any write. Saving the Company clears Frappe's
	cache, which would wipe the token mid-request if the order were reversed.
	The full ERPNext configuration is applied by an RQ worker afterwards: it
	takes minutes and must not block the wizard request.
	"""
	_require_system_manager()
	verify_setup_token(token)
	if profile_data is None:
		company = frappe.get_doc("Company", _default_company())
		result = {
			"status": "ok",
			"name": company.name,
			"company_name": company.company_name,
			"abbr": company.abbr,
		}
	else:
		result = _apply_company_profile(_as_dict(profile_data, _("Company profile")))
	frappe.db.set_single_value("System Settings", "setup_complete", 1)
	_audit(_("Diva setup completed by {0}").format(frappe.session.user))
	frappe.db.commit()
	# Cache writes are not transactional: only burn the token once the row is committed.
	frappe.cache.delete_value(SETUP_TOKEN_CACHE_KEY)
	from diva_guard.setup import _set_status

	_set_status("queued")
	try:
		frappe.enqueue(
			"diva_guard.setup.apply_configuration",
			queue="long",
			company=result["name"],
			abbr=result["abbr"],
			timeout=1800,
		)
		config_status = "queued"
	except Exception as exc:  # Redis down: the owner can retry from the page.
		_set_status("failed", str(exc))
		frappe.log_error(title="Diva setup enqueue", message=str(exc))
		config_status = "failed"
	return {"status": "ok", "config": config_status}


@frappe.whitelist()
def get_setup_status() -> dict:
	"""Progress of the post-wizard configuration, polled by the wizard page."""
	_require_system_manager()
	from diva_guard.setup import get_config_status

	return {"setup_complete": _setup_complete(), "config": get_config_status()}


@frappe.whitelist()
def retry_setup_configuration() -> dict:
	"""Queue the configuration again after a failure."""
	_require_system_manager()
	company = frappe.get_doc("Company", _default_company())
	frappe.enqueue(
		"diva_guard.setup.apply_configuration",
		queue="long",
		company=company.name,
		abbr=company.abbr,
		timeout=1800,
	)
	return {"status": "queued"}
