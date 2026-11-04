"""Contract for the Product Info page/endpoint (DEC-95) and the app registry (DEC-103).

The behaviour lives only on the dev stack (barcode scan, image streaming), so
these are static checks; the live evidence is recorded in
`docs/appendix-erpnext-verification.md`.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD_ENDPOINT = ROOT / "apps" / "diva_guard" / "diva_guard" / "product_info.py"
WWW_PAGE = ROOT / "apps" / "diva_desk" / "diva_desk" / "www" / "product_info.py"
WWW_TEMPLATE = ROOT / "apps" / "diva_desk" / "diva_desk" / "www" / "product_info.html"
ENSURE_SCRIPT = ROOT / "scripts" / "ensure-apps-registered.sh"
START_SCRIPT = ROOT / "scripts" / "start-dev-erpnext.sh"

APP_NAMES = ["pos_next", "diva_guard", "diva_desk", "custom_reports"]


def test_product_info_files_are_committed() -> None:
    """The page and endpoint must exist in git (they were container-only: DEC-103)."""
    assert GUARD_ENDPOINT.is_file()
    assert WWW_PAGE.is_file()
    assert WWW_TEMPLATE.is_file()


def test_page_is_staff_only_and_read_only() -> None:
    page = WWW_PAGE.read_text(encoding="utf-8")
    assert 'frappe.session.user == "Guest"' in page
    assert "redirect-to=/product_info" in page
    # Server API keys/credentials must not appear anywhere in the page layer.
    assert "api_secret" not in page and "api key" not in page.lower()


def test_endpoint_checks_item_permission_before_serving() -> None:
    source = GUARD_ENDPOINT.read_text(encoding="utf-8")
    assert 'frappe.has_permission("Item", "read", item_code)' in source
    # The old direct file URL must not be served anymore: it 403s on private
    # files and leaks unrelated private files to anyone with File access.
    assert '"image": item.get("image") or ""' not in source
    assert "image_endpoint_url(item.name)" in source


def test_image_endpoint_is_contained_in_the_site_files_directory() -> None:
    source = GUARD_ENDPOINT.read_text(encoding="utf-8")
    assert '".." in file_name.parts' in source, "traversal guard missing"
    assert "base.resolve() in candidate.parents" in source
    assert "/private/files/" in source and "/files/" in source


def test_template_uses_the_authorized_image_and_rtl_arabic() -> None:
    template = WWW_TEMPLATE.read_text(encoding="utf-8")
    assert 'lang="ar" dir="rtl"' in template
    assert "diva_guard.product_info.product_info" in template
    # Never hard-code user-facing strings in Python; the static template is
    # Arabic-first by design (docs/19), client-side labels come from the card.
    assert "{% raw %}" in template


def test_ensure_apps_script_lists_all_diva_apps() -> None:
    source = ENSURE_SCRIPT.read_text(encoding="utf-8")
    for app in APP_NAMES:
        assert app in source, app
    assert "bench --site" in source
    assert "docker restart" in source


def test_install_scripts_run_the_ensure_script() -> None:
    for name in ("install_diva_guard.sh", "install_diva_desk.sh", "install_custom_reports.sh"):
        source = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert "ensure-apps-registered.sh" in source, name


def test_start_dev_script_stops_the_configurator_from_clobbering_apps_txt() -> None:
    """DEC-103: `ls -1 apps > sites/apps.txt` in the stock configurator unregisters
    every app its image does not ship; only a first-boot write keeps them."""
    source = START_SCRIPT.read_text(encoding="utf-8")
    assert "ls -1 apps > sites/apps.txt" in source
    assert "[ -f sites/apps.txt ]" in source
    assert "ensure-apps-registered.sh" in source
