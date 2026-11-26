"""First-run setup wizard page (PROD-24).

Serves `/diva-setup`: a token-gated page where a System Manager confirms the
company identity for a fresh store. The page is server-rendered so every string
comes from the translation table (`_()` in the template), never from a literal.

The write path is `diva_guard.api.update_company_profile` followed by
`diva_guard.api.complete_setup`; neither edits ERPNext core, and the token is
single-use and short-lived (PROD-23).
"""

from __future__ import annotations

import frappe

# Languages rendered right-to-left. Kept local so the page does not depend on a
# particular Frappe helper signature.
RTL_LANGS = ("ar", "he", "fa", "ur")

# The only roles allowed to finish first-run setup (same set as the API).
SETUP_ROLES = frozenset({"System Manager"})


def _is_manager() -> bool:
	return bool(SETUP_ROLES.intersection(frappe.get_roles()))


def _setup_complete() -> bool:
	return bool(frappe.db.get_single_value("System Settings", "setup_complete"))


def get_context(context: dict) -> None:
	# Nothing here is cacheable: the token and setup state change per request.
	context.no_cache = 1

	if frappe.session.user in (None, "Guest"):
		frappe.local.flags.redirect_location = "/login?redirect-to=/diva-setup"
		raise frappe.Redirect

	requested = (frappe.form_dict.get("lang") or "").strip()
	if requested in ("ar", "en"):
		# Display only; it selects which translation catalog `_()` resolves.
		frappe.local.lang = requested

	lang = requested or frappe.local.lang or "en"
	is_manager = _is_manager()
	complete = _setup_complete()
	config_status = {"status": "pending", "error": ""}
	if is_manager:
		from diva_guard.setup import get_config_status

		config_status = get_config_status()

	context.lang_code = lang
	context.is_rtl = lang in RTL_LANGS
	context.is_manager = is_manager
	context.setup_complete = complete
	# The wizard commits the Company before the configuration runs. A reload in
	# that window must keep showing progress (and the retry button), not the
	# "already complete" card.
	context.setup_pending_config = complete and config_status.get("status") != "ok"
	context.config_status = config_status
	context.token = None
	context.csrf_token = frappe.sessions.get_csrf_token()

	if is_manager and not complete:
		from diva_guard.api import get_setup_token

		try:
			context.token = get_setup_token()["token"]
		except frappe.ValidationError:
			# Setup raced to complete between the two reads; render the done card.
			context.setup_complete = True
			context.token = None
