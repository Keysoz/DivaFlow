"""Arabic coverage for the Diva strings (DEC-102).

Every user-facing string in the two governed Diva layers must have an Arabic
translation: either a `Translation` record in `infra/erpnext-config/config.yaml`
or a line in `ar_po_allowlist.txt` for strings already translated by ERPNext's
bundled `ar.po`. CI fails on a missing key (AGENTS.md localization rule).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _desk_strings() -> set[str]:
    text = (ROOT / "apps" / "diva_desk" / "diva_desk" / "public" / "js" / "diva_desk.js").read_text(
        encoding="utf-8"
    )
    return set(re.findall(r'__\(\s*"([^"]+)"', text)) | set(re.findall(r"__\(\s*'([^']+)'", text))


def _guard_strings() -> set[str]:
    out: set[str] = set()
    for path in (ROOT / "apps" / "diva_guard" / "diva_guard").rglob("*.py"):
        out |= set(re.findall(r'_\(\s*"([^"]+)"', path.read_text(encoding="utf-8")))
    return out


def _config_translations() -> set[str]:
    config: dict[str, Any] = yaml.safe_load(
        (ROOT / "infra" / "erpnext-config" / "config.yaml").read_text(encoding="utf-8")
    )
    return {
        record["match"]["source_text"]
        for record in config.get("records", [])
        if record.get("doctype") == "Translation"
        and record.get("match", {}).get("language") == "ar"
    }


def _allowlist() -> set[str]:
    path = Path(__file__).with_name("ar_po_allowlist.txt")
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def test_desk_strings_have_arabic() -> None:
    covered = _config_translations() | _allowlist()
    missing = sorted(string for string in _desk_strings() if string not in covered)
    assert not missing, f"missing Arabic for diva_desk.js: {missing}"


def test_guard_strings_have_arabic() -> None:
    covered = _config_translations() | _allowlist()
    missing = sorted(string for string in _guard_strings() if string not in covered)
    assert not missing, f"missing Arabic for diva_guard: {missing}"


def test_trading_terms_are_corrected() -> None:
    """The ar.po mistranslations and the glossary terms we override (DEC-102)."""
    translations = _config_translations()
    # These were wrong or missing in ERPNext's ar.po.
    for source in (
        "Item",
        "Amount",
        "Due Date",
        "Draft",
        "Shift",
        "Nos",
        "Dozen",
        "Warehouse",
        "Item Group",
    ):
        assert source in translations, source
