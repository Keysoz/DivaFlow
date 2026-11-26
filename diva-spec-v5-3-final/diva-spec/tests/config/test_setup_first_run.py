"""Static contract for the first-run provisioning module (PROD-25).

`diva_guard.setup` runs inside Frappe, which is not installed in the test
environment. These checks lock the two bugs found on a real fresh site: a bare
`bench new-site` has no ERPNext setup fixtures (so the first Company fails on
the missing `Transit` warehouse type) and no `System Settings.language` (so
address rendering raises `UnboundLocalError`).
"""

from __future__ import annotations

import ast
from pathlib import Path

SETUP = Path(__file__).resolve().parents[2] / "apps" / "diva_guard" / "diva_guard" / "setup.py"


def source() -> str:
    return SETUP.read_text(encoding="utf-8")


def defined_functions() -> set[str]:
    tree = ast.parse(source())
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def test_first_run_functions_exist() -> None:
    assert {
        "prepare_first_run",
        "ensure_site_defaults",
        "ensure_erpnext_fixtures",
        "seed_translations",
        "ensure_api_credentials",
        "apply_configuration",
        "get_config_status",
    } <= defined_functions()


def test_prepare_first_run_sets_defaults_and_fixtures() -> None:
    text = source()
    body = text[text.index("def prepare_first_run(") :]
    body = body[: body.index("def ", body.index("return {"))]
    assert "ensure_site_defaults()" in body
    assert "ensure_erpnext_fixtures()" in body
    assert "seed_translations()" in body


def test_language_default_prevents_the_unbound_locale_error() -> None:
    text = source()
    body = text[text.index("def ensure_site_defaults(") :]
    body = body[: body.index("def ", 10)]
    assert '"System Settings", "language", "ar"' in body
    assert '"System Settings", "country", "Egypt"' in body
    assert '"default_currency", "EGP"' in body


def test_arabic_is_the_site_default_language() -> None:
    """docs/19: Arabic is primary; staff start RTL and may switch to English."""
    text = source()
    body = text[text.index("def ensure_site_defaults(") :]
    body = body[: body.index("def ", 10)]
    assert '"language", "ar"' in body
    assert '"language", "en"' not in body


def test_erpnext_fixtures_are_installed_when_transit_is_missing() -> None:
    text = source()
    body = text[text.index("def ensure_erpnext_fixtures(") :]
    body = body[: body.index("def ", 10)]
    assert 'frappe.db.exists("Warehouse Type", "Transit")' in body
    assert 'install_fixtures.install(country="Egypt")' in body


def test_configuration_uses_stored_api_credentials_not_the_admin_password() -> None:
    text = source()
    body = text[text.index("def apply_configuration(") :]
    assert 'frappe.conf.get("diva_api_key")' in body
    assert 'frappe.conf.get("diva_api_secret")' in body
    assert "ERPNEXT_PASSWORD" not in body
    assert "Administrator" not in body


def test_configuration_status_is_visible_to_the_wizard() -> None:
    text = source()
    assert "def get_config_status()" in text
    for state in ('"pending"', '"running"', '"ok"', '"failed"'):
        assert state in text
