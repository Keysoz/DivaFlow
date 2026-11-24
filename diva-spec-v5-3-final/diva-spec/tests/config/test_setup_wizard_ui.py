"""Static contract for the first-run setup wizard page (PROD-24).

`tests/config/test_i18n_coverage.py` scans Python and `diva_desk.js` only, so a
template could ship hard-coded English or Arabic without failing CI. These
checks close that gap: every `_()` string in the page must have an Arabic
translation, and no Arabic may appear as a literal outside `_()`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "apps" / "diva_guard" / "diva_guard"
PAGE = GUARD / "www" / "diva-setup.html"
CONTROLLER = GUARD / "www" / "diva_setup.py"
CONFIG = ROOT / "infra" / "erpnext-config" / "config.yaml"

DOUBLE = re.compile(r'_\("([^"]+)"\)')
SINGLE = re.compile(r"_\(\'([^\']+)\'\)")
ARABIC = re.compile(r"[\u0600-\u06FF]")


def page_text() -> str:
    return PAGE.read_text(encoding="utf-8")


def page_strings() -> set[str]:
    text = page_text()
    return set(DOUBLE.findall(text)) | set(SINGLE.findall(text))


def covered_strings() -> set[str]:
    config: dict[str, Any] = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    records = {
        record["match"]["source_text"]
        for record in config.get("records", [])
        if record.get("doctype") == "Translation"
        and record.get("match", {}).get("language") == "ar"
    }
    allowlist = {
        line.strip()
        for line in (ROOT / "tests" / "config" / "ar_po_allowlist.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    }
    return records | allowlist


def test_wizard_page_exists() -> None:
    assert PAGE.is_file(), PAGE
    assert CONTROLLER.is_file(), CONTROLLER


def test_every_page_string_has_arabic() -> None:
    missing = sorted(page_strings() - covered_strings())
    assert not missing, f"missing Arabic for diva-setup.html: {missing}"


def test_no_hardcoded_arabic_outside_translation_call() -> None:
    stripped = DOUBLE.sub("", SINGLE.sub("", page_text()))
    assert not ARABIC.search(stripped), "Arabic literal outside _() in diva-setup.html"


def test_page_sends_the_keys_the_api_expects() -> None:
    """The wizard saves and completes in one call; `update_company_profile` reads `abbr`."""
    text = page_text()
    assert "profile_data" in text
    assert "token: TOKEN" in text
    assert "abbr:" in text
    assert "company_abbr" not in text
    assert "complete_setup" in text


def test_page_posts_with_csrf_token() -> None:
    assert "X-Frappe-CSRF-Token" in page_text()


def test_page_can_be_prefilled_and_respects_frozen_fields() -> None:
    text = page_text()
    assert "get_company_profile" in text
    assert "can_change_name" in text
    assert "can_change_abbr" in text


def test_controller_redirects_guests_to_login() -> None:
    text = CONTROLLER.read_text(encoding="utf-8")
    assert "/login?redirect-to=/diva-setup" in text
    assert "frappe.Redirect" in text


def test_controller_is_uncached_and_token_gated() -> None:
    text = CONTROLLER.read_text(encoding="utf-8")
    assert "context.no_cache = 1" in text
    assert "get_setup_token" in text
    assert "System Manager" in text
