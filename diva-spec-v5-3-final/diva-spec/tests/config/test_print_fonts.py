"""The print formats bundle their Arabic font (E-15, DEC-98).

No print may depend on a font CDN: the store network can block it and the
receipt must render offline. Every print format references the bundled Cairo
files that ship with custom_reports, and those files exist.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRINT_DIRS = [
    ROOT / "infra" / "erpnext-config" / "print_formats",
    ROOT / "apps" / "custom_reports" / "custom_reports" / "print_format",
]
FONT_DIR = ROOT / "apps" / "custom_reports" / "custom_reports" / "public" / "fonts"
FONT_URL = re.compile(r'url\("(/assets/custom_reports/fonts/[^"]+)"\)')


def print_formats() -> list[Path]:
    return sorted(path for folder in PRINT_DIRS for path in folder.glob("*.html"))


def test_print_formats_use_the_bundled_font() -> None:
    formats = print_formats()
    assert formats, "no print formats found"
    for path in formats:
        html = path.read_text(encoding="utf-8")
        assert "@font-face" in html, f"{path.name} has no @font-face"
        assert '"Diva Cairo"' in html, f"{path.name} does not use Diva Cairo"
        assert 'font-family: "Diva Cairo"' in html, f"{path.name} declares the wrong family"


def test_no_print_format_uses_a_font_cdn() -> None:
    for path in print_formats():
        html = path.read_text(encoding="utf-8")
        assert "fonts.googleapis.com" not in html, f"{path.name} uses the Google Fonts CSS"
        assert "fonts.gstatic.com" not in html, f"{path.name} uses the Google Fonts files"


def test_every_referenced_font_file_exists() -> None:
    referenced: set[str] = set()
    for path in print_formats():
        referenced.update(FONT_URL.findall(path.read_text(encoding="utf-8")))
    assert referenced, "no bundled font is referenced"
    for url in referenced:
        font = FONT_DIR / Path(url).name
        assert font.is_file(), f"{url} is referenced but {font} is missing"
        assert font.stat().st_size > 10_000, f"{font.name} looks empty"


def test_the_font_license_ships_with_it() -> None:
    license_file = FONT_DIR / "OFL.txt"
    assert license_file.is_file()
    assert "SIL OPEN FONT LICENSE" in license_file.read_text(encoding="utf-8").upper()
