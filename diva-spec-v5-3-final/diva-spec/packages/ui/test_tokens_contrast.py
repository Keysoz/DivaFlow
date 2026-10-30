"""Contrast checks for the Diva design tokens (BRAND-01, DEC-92).

Every text pair must meet WCAG AA (4.5:1). The documented ratios in
``docs/27-brand-and-design-tokens.md`` must stay accurate within 0.1.
Gold on the light page is documented as decorative only (2.2:1) and must never
be used for text; the matching test enforces that it stays below AA.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TOKENS = json.loads((HERE / "tokens.json").read_text(encoding="utf-8"))
CSS = (HERE / "tokens.css").read_text(encoding="utf-8").lower()

# theme, foreground token, background token, documented ratio
TEXT_PAIRS = [
    ("light", "text", "page", 14.6),
    ("light", "text", "panel", 15.8),
    ("light", "text-secondary", "page", 6.5),
    ("light", "on-primary", "primary", 11.5),
    ("light", "on-gold", "gold", 6.6),
    ("light", "gold", "primary", 4.8),
    ("light", "success", "page", 4.8),
    ("light", "warning", "page", 4.7),
    ("light", "error", "page", 6.5),
    ("dark", "text", "page", 15.0),
    ("dark", "text-secondary", "page", 8.4),
    ("dark", "gold", "page", 8.6),
    ("dark", "success", "page", 9.4),
    ("dark", "warning", "page", 9.1),
    ("dark", "error", "page", 8.0),
]

DECORATIVE_PAIRS = [
    ("light", "gold", "page", 2.2),
]


def _linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    value = hex_color.lstrip("#")
    red, green, blue = (int(value[index : index + 2], 16) / 255 for index in (0, 2, 4))
    return 0.2126 * _linear(red) + 0.7152 * _linear(green) + 0.0722 * _linear(blue)


def contrast(foreground: str, background: str) -> float:
    high, low = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize(("theme", "foreground", "background", "documented"), TEXT_PAIRS)
def test_text_pair_meets_wcag_aa(
    theme: str, foreground: str, background: str, documented: float
) -> None:
    ratio = contrast(TOKENS[theme][foreground], TOKENS[theme][background])
    assert ratio >= 4.5, f"{theme}: {foreground} on {background} is {ratio:.2f}:1 (needs 4.5:1)"
    assert ratio == pytest.approx(documented, abs=0.1), (
        f"{theme}: {foreground} on {background} measured {ratio:.2f}, docs/27 says {documented}"
    )


@pytest.mark.parametrize(("theme", "foreground", "background", "documented"), DECORATIVE_PAIRS)
def test_decorative_pair_is_not_text(
    theme: str, foreground: str, background: str, documented: float
) -> None:
    ratio = contrast(TOKENS[theme][foreground], TOKENS[theme][background])
    assert ratio == pytest.approx(documented, abs=0.1)
    assert ratio < 4.5, (
        f"{theme}: {foreground} on {background} is now {ratio:.2f}:1; "
        "it may not be decorative anymore"
    )


def test_css_contains_every_palette_value() -> None:
    for theme in ("light", "dark"):
        for token, value in TOKENS[theme].items():
            assert value.lower() in CSS, f"{theme}.{token} ({value}) is missing from tokens.css"


def test_css_declares_typography_and_radius() -> None:
    for token in (
        "--diva-font-sans",
        "--diva-font-brand",
        "--diva-text-base",
        "--diva-space-4",
        "--diva-radius-pill",
    ):
        assert token in CSS, f"{token} is missing from tokens.css"


def test_light_and_dark_tokens_match() -> None:
    assert set(TOKENS["light"]) == set(TOKENS["dark"]), (
        "light and dark must expose the same color tokens"
    )
