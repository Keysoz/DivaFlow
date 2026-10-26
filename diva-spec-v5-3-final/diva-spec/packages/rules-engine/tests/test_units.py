"""Tests for the Dozen/Nos unit conversion model (DEC-20, RULE-UOM).

Stock is Nos (pieces); buying, selling and prices are Dozen.
1 Dozen = 12 Nos (PCS_PER_DOZEN). Floats and bools are rejected.
"""

from decimal import Decimal

import pytest

from rules_engine.units import (
    PCS_PER_DOZEN,
    UomError,
    dozen_to_pieces,
    is_whole_dozen,
    pieces_to_dozen,
)


def test_pcs_per_dozen_is_twelve() -> None:
    """The constant that ties Dozen to Nos is 12 (DEC-20)."""
    assert PCS_PER_DOZEN == 12


# -- dozen_to_pieces ----------------------------------------------------------


@pytest.mark.parametrize(
    ("dozens", "expected_pieces"),
    [
        (1, 12),
        (2, 24),
        (Decimal("2.5"), 30),
        ("2.5", 30),
        (Decimal("1"), 12),
        ("1", 12),
    ],
)
def test_dozen_to_pieces_accepts_int_str_decimal(
    dozens: Decimal | int | str, expected_pieces: int
) -> None:
    assert dozen_to_pieces(dozens) == expected_pieces


def test_dozen_to_pieces_rejects_non_whole_dozen() -> None:
    """0.1 Dozen = 1.2 pieces, which is not whole -> UomError."""
    with pytest.raises(UomError):
        dozen_to_pieces(Decimal("0.1"))


def test_dozen_to_pieces_rejects_invalid_string() -> None:
    with pytest.raises(UomError):
        dozen_to_pieces("not-a-number")


def test_dozen_to_pieces_rejects_float() -> None:
    with pytest.raises(TypeError):
        dozen_to_pieces(1.5)  # type: ignore[arg-type]


def test_dozen_to_pieces_rejects_bool() -> None:
    with pytest.raises(TypeError):
        dozen_to_pieces(True)  # type: ignore[arg-type]


# -- pieces_to_dozen ----------------------------------------------------------


def test_pieces_to_dozen_returns_exact_decimal() -> None:
    """pieces_to_dozen(18) must equal Decimal("18") / 12, not a float."""
    result = pieces_to_dozen(18)
    assert result == Decimal("18") / 12
    assert result == Decimal("1.5")
    assert isinstance(result, Decimal)


def test_pieces_to_dozen_accepts_int_str_decimal() -> None:
    assert pieces_to_dozen(12) == Decimal("1")
    assert pieces_to_dozen("24") == Decimal("2")
    assert pieces_to_dozen(Decimal("6")) == Decimal("0.5")


def test_pieces_to_dozen_rejects_float() -> None:
    with pytest.raises(TypeError):
        pieces_to_dozen(1.0)  # type: ignore[arg-type]


def test_pieces_to_dozen_rejects_bool() -> None:
    with pytest.raises(TypeError):
        pieces_to_dozen(False)  # type: ignore[arg-type]


# -- is_whole_dozen -----------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        1,
        2,
        Decimal("2.5"),
        Decimal("0.5"),
        "0.5",
        "1",
        Decimal("1") / 3,  # 4 pieces, whole
    ],
)
def test_is_whole_dozen_true(value: Decimal | int | str) -> None:
    assert is_whole_dozen(value) is True


@pytest.mark.parametrize(
    "value",
    [
        Decimal("0.1"),  # 1.2 pieces
        Decimal("1") / 7,  # ~1.714 pieces
        "0.3",  # 3.6 pieces
    ],
)
def test_is_whole_dozen_false(value: Decimal | int | str) -> None:
    assert is_whole_dozen(value) is False
