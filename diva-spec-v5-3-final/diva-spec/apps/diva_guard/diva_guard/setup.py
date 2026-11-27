"""First-run provisioning for a fresh Diva store (PROD-25).

The installer creates an empty ERPNext site, installs the Diva apps and calls
:func:`prepare_first_run`. The web wizard then creates the Company with the
owner's name and abbreviation, and :func:`apply_configuration` applies
``infra/erpnext-config/config.yaml`` once the wizard has committed.

The config is applied through the same REST script the rest of the project uses
(``infra/erpnext-config/apply.py``), so no rule or setting is duplicated here.
It runs in an RQ worker, not in the web request: a first apply takes minutes and
the wizard must be able to show progress instead of timing out.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import frappe

CONFIG_STATUS_KEY = "diva_guard:config_status"
CONFIG_STATUS_TTL_SECONDS = 7 * 24 * 3600
DEFAULT_CONFIG = "/home/frappe/frappe-bench/infra/erpnext-config/config.yaml"
DEFAULT_APPLY = "/home/frappe/frappe-bench/infra/erpnext-config/apply.py"
DEFAULT_URL = "http://frontend:8080"


def _config_path() -> Path:
	return Path(os.environ.get("DIVA_CONFIG_PATH", DEFAULT_CONFIG))


def _apply_path() -> Path:
	return Path(os.environ.get("DIVA_APPLY_PATH", DEFAULT_APPLY))


def _set_status(status: str, error: str = "") -> None:
	frappe.cache.set_value(
		CONFIG_STATUS_KEY,
		{"status": status, "error": error[:4000]},
		expires_in_sec=CONFIG_STATUS_TTL_SECONDS,
	)


def get_config_status() -> dict:
	"""Return the last config run for the wizard and the installer."""
	value = frappe.cache.get_value(CONFIG_STATUS_KEY)
	if not value:
		return {"status": "pending", "error": ""}
	return value


def ensure_site_defaults() -> None:
	"""Set the language and country defaults a bare site lacks.

	A site created with ``bench new-site`` has no ``System Settings.language``;
	without it Frappe's address rendering fails with an unbound locale value.
	Arabic is the site default because Arabic is primary (docs/19): cashiers and
	store staff start RTL, and each user can switch to English per profile.
	Egypt and EGP are the store's defaults (DEC-20).
	"""
	if not frappe.db.get_single_value("System Settings", "language"):
		frappe.db.set_single_value("System Settings", "language", "ar")
	if not frappe.db.get_single_value("System Settings", "country"):
		frappe.db.set_single_value("System Settings", "country", "Egypt")
	frappe.db.set_single_value("System Settings", "date_format", "dd-mm-yyyy")
	frappe.db.set_single_value("System Settings", "time_format", "HH:mm")
	frappe.db.set_single_value("Global Defaults", "country", "Egypt")
	frappe.db.set_single_value("Global Defaults", "default_currency", "EGP")
	frappe.db.commit()


def ensure_erpnext_fixtures() -> bool:
	"""Install ERPNext's setup fixtures (warehouse types, UOMs, item groups).

	``bench new-site --install-app erpnext`` does not run them; the ERPNext
	setup wizard does. Without the ``Transit`` warehouse type, creating the
	first Company fails.
	"""
	if frappe.db.exists("Warehouse Type", "Transit"):
		return False
	from erpnext.setup.setup_wizard.operations import install_fixtures

	install_fixtures.install(country="Egypt")
	frappe.db.commit()
	return True


def seed_translations() -> int:
	"""Insert the Arabic records before the wizard renders.

	The full config is applied after setup, but the wizard itself needs its
	Arabic strings first: Arabic is primary and the page is RTL.
	"""
	import yaml

	path = _config_path()
	if not path.is_file():
		frappe.throw(f"Configuration file not found: {path}")
	config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
	count = 0
	for record in config.get("records", []):
		if record.get("doctype") != "Translation":
			continue
		match = record.get("match") or {}
		if match.get("language") != "ar":
			continue
		source = match.get("source_text")
		translated = (record.get("set") or {}).get("translated_text")
		if not source or not translated:
			continue
		existing = frappe.db.get_value("Translation", {"language": "ar", "source_text": source}, "name")
		if existing:
			frappe.db.set_value("Translation", existing, "translated_text", translated)
		else:
			frappe.get_doc(
				{
					"doctype": "Translation",
					"language": "ar",
					"source_text": source,
					"translated_text": translated,
				}
			).insert(ignore_permissions=True)
		count += 1
	frappe.db.commit()
	return count


def prepare_first_run() -> dict:
	"""Prepare a newly created site for the wizard (idempotent)."""
	translations = seed_translations()
	ensure_site_defaults()
	fixtures = ensure_erpnext_fixtures()
	# A new site is not "set up" until the owner finishes the wizard; ERPNext may
	# otherwise send /app to its own setup wizard first.
	frappe.db.set_single_value("System Settings", "setup_complete", 0)
	frappe.db.commit()
	frappe.clear_cache()
	_set_status("pending")
	return {
		"translations": translations,
		"fixtures_installed": fixtures,
		"setup_complete": 0,
	}


def ensure_api_credentials() -> dict:
	"""Generate the Administrator API key used by the config job.

	The plaintext secret is written only to ``site_config.json`` (mode 600 in the
	sites volume); it is never logged or returned by an endpoint. Re-running is a
	no-op while the stored key still matches the user, so a resumed installer does
	not invalidate credentials a queued job is already using.
	"""
	from frappe.core.doctype.user.user import generate_keys
	from frappe.installer import update_site_config

	stored_key = frappe.conf.get("diva_api_key")
	stored_secret = frappe.conf.get("diva_api_secret")
	current_key = frappe.db.get_value("User", "Administrator", "api_key")
	if stored_key and stored_secret and current_key == stored_key:
		return {"status": "unchanged"}

	keys = generate_keys("Administrator")
	update_site_config("diva_api_key", keys["api_key"])
	update_site_config("diva_api_secret", keys["api_secret"])
	frappe.db.commit()
	return {"status": "ok"}


def apply_configuration(company: str, abbr: str) -> dict:
	"""Apply ``config.yaml`` for the identity chosen in the wizard.

	Run by an RQ worker after ``complete_setup`` commits. Idempotent: a retry
	after a partial run only adds what is missing.
	"""
	config_path, apply_path = _config_path(), _apply_path()
	if not config_path.is_file() or not apply_path.is_file():
		message = f"Configuration files not found: {config_path}, {apply_path}"
		_set_status("failed", message)
		frappe.log_error(title="Diva setup configuration", message=message)
		return {"status": "failed", "error": message}

	api_key = frappe.conf.get("diva_api_key")
	api_secret = frappe.conf.get("diva_api_secret")
	if not (api_key and api_secret):
		message = "Diva API credentials are missing; run diva_guard.setup.ensure_api_credentials."
		_set_status("failed", message)
		frappe.log_error(title="Diva setup configuration", message=message)
		return {"status": "failed", "error": message}

	env = os.environ.copy()
	env.update(
		{
			"ERPNEXT_URL": os.environ.get("DIVA_APPLY_URL", DEFAULT_URL),
			"ERPNEXT_API_KEY": str(api_key),
			"ERPNEXT_API_SECRET": str(api_secret),
		}
	)
	command = [
		sys.executable,
		str(apply_path),
		"--config",
		str(config_path),
		"--apply",
		"--strict",
		"--company",
		company,
		"--abbr",
		abbr,
	]
	_set_status("running")
	try:
		completed = subprocess.run(
			command,
			env=env,
			capture_output=True,
			text=True,
			timeout=1800,
			check=False,
		)
	except subprocess.TimeoutExpired:
		message = "Configuration timed out after 30 minutes."
		_set_status("failed", message)
		frappe.log_error(title="Diva setup configuration", message=message)
		return {"status": "failed", "error": message}

	if completed.returncode != 0:
		tail = (completed.stderr or completed.stdout or "").strip()[-4000:]
		_set_status("failed", tail or "Configuration failed.")
		frappe.log_error(
			title="Diva setup configuration",
			message=f"apply.py exited {completed.returncode}\n\n{tail}",
		)
		return {"status": "failed", "error": tail}

	_set_status("ok")
	frappe.logger("diva_guard").info(
		"Diva configuration applied for %s (%s): %s",
		company,
		abbr,
		(completed.stdout or "").strip()[-2000:],
	)
	return {"status": "ok"}
