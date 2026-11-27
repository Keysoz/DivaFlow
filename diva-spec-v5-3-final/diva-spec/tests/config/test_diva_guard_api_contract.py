"""Static contract for the diva_guard API (TASK-E-14a, PROD-19, PROD-23).

The module runs inside Frappe, which is not installed in this test environment,
so these checks read the source. They exist because an earlier rewrite of this
file silently dropped the discount approval and QR endpoints and added an
undeclared Pillow dependency; both would only surface in production.
"""

from __future__ import annotations

import ast
from pathlib import Path

API = Path(__file__).resolve().parents[2] / "apps" / "diva_guard" / "diva_guard" / "api.py"

WHITELISTED = {
    "approve_discount",
    "qr_svg",
    "verify_manager_pin",
    "get_company_profile",
    "update_company_profile",
    "get_setup_token",
    "verify_setup_token",
    "complete_setup",
    "get_setup_status",
    "retry_setup_configuration",
}


def source() -> str:
    return API.read_text(encoding="utf-8")


def tree() -> ast.Module:
    return ast.parse(source())


def defined_functions() -> set[str]:
    return {node.name for node in tree().body if isinstance(node, ast.FunctionDef)}


def test_shipped_pin_endpoints_are_still_present() -> None:
    """E-14a: the discount approval and the QR renderer must not disappear."""
    functions = defined_functions()
    assert {"approve_discount", "qr_svg", "hash_pin", "_verify_pin"} <= functions


def test_wizard_endpoints_exist() -> None:
    assert defined_functions() >= WHITELISTED


def test_no_undeclared_image_library() -> None:
    """Logo validation uses magic bytes; PIL is not a dependency of diva_guard."""
    forbidden = ("from PIL", "import PIL", "Pillow")
    assert not [name for name in forbidden if name in source()]


def test_setup_flag_lives_on_system_settings() -> None:
    """`setup_complete` is a System Settings field; Site Settings has no such field."""
    text = source()
    assert 'get_single_value("System Settings", "setup_complete")' in text
    assert 'set_single_value("System Settings", "setup_complete", 1)' in text
    site_settings = "Site Settings"
    assert site_settings not in text


def test_setup_token_is_hashed_and_single_use() -> None:
    text = source()
    assert "_token_digest(token)" in text
    assert "hmac.compare_digest" in text
    assert "delete_value(SETUP_TOKEN_CACHE_KEY)" in text


def test_profile_writes_are_system_manager_only() -> None:
    text = source()
    assert 'SETUP_ROLES = frozenset({"System Manager"})' in text
    assert "_require_system_manager()" in text


def test_name_and_abbr_freeze_after_a_transaction() -> None:
    text = source()
    assert "The company name cannot change after the first transaction." in text
    assert "The company abbreviation cannot change after the first transaction." in text
    assert "def _has_transactions(" in text


def test_abbr_freeze_accounts_for_warehouses() -> None:
    """Warehouse names embed the abbreviation, so it locks once one exists."""
    text = source()
    assert "def _abbr_locked(" in text
    assert 'frappe.db.exists("Warehouse", {"company": company})' in text


def test_logo_is_validated_by_signature_not_extension() -> None:
    text = source()
    assert "LOGO_SIGNATURES" in text
    assert "MAX_LOGO_BYTES" in text


def test_complete_setup_verifies_token_before_writing() -> None:
    """Saving the Company clears the cache; verifying after the write fails every time."""
    text = source()
    body = text[text.index("def complete_setup(") :]
    assert body.index("verify_setup_token(token)") < body.index("_apply_company_profile(")


def test_audit_uses_valid_activity_log_options() -> None:
    """Activity Log.operation only allows Login/Logout/Impersonate, so it stays unset."""
    text = source()
    assert '"operation": "Diva Setup"' not in text
    assert '"status": "Success"' in text


def test_fresh_site_returns_an_empty_profile_not_an_error() -> None:
    """The wizard opens before a Company exists, so the read must not call _default_company."""
    text = source()
    assert "def _empty_profile()" in text
    body = text[text.index("def get_company_profile(") :]
    body = body[: body.index("@frappe.whitelist", 10)]
    assert "_empty_profile()" in body
    assert "_default_company()" not in body


def test_wizard_creates_the_company_on_a_fresh_site() -> None:
    """ERPNext derives accounts and warehouse names from the abbr at creation time."""
    text = source()
    assert "def _company_to_edit(" in text
    assert '"chart_of_accounts": "Standard"' in text
    assert "ensure_erpnext_fixtures()" in text
    assert "ensure_site_defaults()" in text


def test_complete_setup_queues_configuration_after_the_commit() -> None:
    """The worker must not read a Company that is not committed yet."""
    text = source()
    body = text[text.index("def complete_setup(") :]
    body = body[: body.index("@frappe.whitelist", 10)]
    assert "frappe.enqueue(" in body
    assert body.index("frappe.db.commit()") < body.index("frappe.enqueue(")
    assert '_set_status("queued")' in body


def test_config_job_runs_the_shared_apply_script() -> None:
    """Rules and settings stay in infra/erpnext-config; the job only invokes it."""
    setup_module = API.parent / "setup.py"
    text = setup_module.read_text(encoding="utf-8")
    assert '"--apply"' in text
    assert '"--strict"' in text
    assert '"--company"' in text
    assert '"--abbr"' in text
    assert "ERPNEXT_API_KEY" in text
    assert "DIVA_APPLY_URL" in text
