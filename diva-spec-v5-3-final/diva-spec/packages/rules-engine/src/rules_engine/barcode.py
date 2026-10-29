"""Internal EAN-13 barcodes for Diva (DEC-32).

The store uses GS1's in-store prefix range 20-29 for barcodes it creates itself.
Existing supplier barcodes are kept; this module only generates and validates
the internal numbers. The layout is:

    PP NNNNNNNNNN C
    │  │          └─ check digit
    │  └──────────── 10-digit sequence (unique per prefix)
    └─────────────── 2-digit GS1 in-store prefix (20-29)
"""

from __future__ import annotations

from collections.abc import Iterable

EAN13_LENGTH = 13
_SEQUENCE_DIGITS = 10
_MAX_SEQUENCE = 10**_SEQUENCE_DIGITS - 1
INTERNAL_PREFIXES = tuple(range(20, 30))


class BarcodeError(ValueError):
    """An EAN-13 barcode cannot be generated or validated."""


def _require_digits(value: str, length: int) -> None:
    if len(value) != length or not value.isdigit():
        raise BarcodeError(f"expected {length} digits, got {value!r}")


def ean13_check_digit(first_twelve: str) -> int:
    """Return the EAN-13 check digit for the first 12 digits."""
    _require_digits(first_twelve, 12)
    total = sum((3 if index % 2 else 1) * int(digit) for index, digit in enumerate(first_twelve))
    return (10 - total % 10) % 10


def format_ean13(first_twelve: str) -> str:
    """Append the check digit to a 12-digit body."""
    return first_twelve + str(ean13_check_digit(first_twelve))


def is_valid_ean13(code: str) -> bool:
    """True when ``code`` is exactly 13 digits with a valid check digit."""
    if len(code) != EAN13_LENGTH or not code.isdigit():
        return False
    return format_ean13(code[:12]) == code


def is_internal_ean13(code: str) -> bool:
    """True for a valid EAN-13 inside the GS1 in-store prefix range 20-29."""
    return is_valid_ean13(code) and 20 <= int(code[:2]) <= 29


def generate_ean13(sequence: int, prefix: int = 20) -> str:
    """Build an internal EAN-13 from a prefix and a 10-digit sequence."""
    if prefix not in INTERNAL_PREFIXES:
        raise BarcodeError(f"prefix must be between 20 and 29, got {prefix}")
    if not 0 <= sequence <= _MAX_SEQUENCE:
        raise BarcodeError(f"sequence must be between 0 and {_MAX_SEQUENCE}, got {sequence}")
    return format_ean13(f"{prefix:02d}{sequence:0{_SEQUENCE_DIGITS}d}")


def next_internal_ean13(existing: Iterable[str], *, prefix: int = 20, start: int = 1) -> str:
    """Return the next unused internal EAN-13 for one prefix.

    Existing supplier barcodes are ignored. Internal barcodes for other
    prefixes do not consume this prefix's sequence space.
    """
    if prefix not in INTERNAL_PREFIXES:
        raise BarcodeError(f"prefix must be between 20 and 29, got {prefix}")
    if not 0 <= start <= _MAX_SEQUENCE:
        raise BarcodeError(f"start must be between 0 and {_MAX_SEQUENCE}, got {start}")

    used: set[int] = set()
    highest = -1
    for code in existing:
        if not is_internal_ean13(code) or int(code[:2]) != prefix:
            continue
        sequence = int(code[2:12])
        used.add(sequence)
        highest = max(highest, sequence)

    sequence = max(start, highest + 1)
    while sequence in used:
        sequence += 1
    if sequence > _MAX_SEQUENCE:
        raise BarcodeError(f"no free EAN-13 left for prefix {prefix}")
    return generate_ean13(sequence, prefix)
