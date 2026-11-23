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
