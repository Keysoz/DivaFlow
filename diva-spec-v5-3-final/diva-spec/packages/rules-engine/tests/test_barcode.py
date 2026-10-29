"""Tests for the internal EAN-13 generator (DEC-32, TASK-E-13 slice)."""

import pytest

from rules_engine import (
    BarcodeError,
    ean13_check_digit,
    format_ean13,
    generate_ean13,
    is_internal_ean13,
    is_valid_ean13,
    next_internal_ean13,
)


def test_known_ean13_check_digits() -> None:
    assert is_valid_ean13("4006381333931")
    assert is_valid_ean13("2100001000011")
    assert is_valid_ean13("2100001000028")
    assert not is_valid_ean13("2100001000012")


def test_format_adds_check_digit() -> None:
    assert format_ean13("200000000001") == "2000000000015"
    assert ean13_check_digit("400638133393") == 1


def test_generate_uses_prefix_and_sequence() -> None:
    assert generate_ean13(1, prefix=20) == "2000000000015"
    assert generate_ean13(1, prefix=21) == "2100000000012"
    assert is_internal_ean13(generate_ean13(12345, prefix=29))


def test_generate_rejects_bad_prefix_and_sequence() -> None:
    with pytest.raises(BarcodeError, match="prefix"):
        generate_ean13(1, prefix=19)
    with pytest.raises(BarcodeError, match="prefix"):
        generate_ean13(1, prefix=30)
    with pytest.raises(BarcodeError, match="sequence"):
        generate_ean13(-1)
    with pytest.raises(BarcodeError, match="sequence"):
        generate_ean13(10**10)


def test_next_internal_skips_used_and_external_codes() -> None:
    existing = [
        "2100001000011",
        "2100001000028",
        "4006381333931",  # supplier barcode
        "2200000000016",  # other prefix
        "not-a-barcode",
    ]
    assert next_internal_ean13(existing, prefix=21) == "2100001000035"


def test_next_internal_starts_at_requested_sequence() -> None:
    assert next_internal_ean13([], prefix=20, start=42) == generate_ean13(42, prefix=20)


def test_invalid_ean13_helpers() -> None:
    assert not is_valid_ean13("123")
    assert not is_valid_ean13("abcdefghijklm")
    assert not is_internal_ean13("4006381333931")
    with pytest.raises(BarcodeError):
        format_ean13("123")
