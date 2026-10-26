"""Tests for the Dozen/Nos unit conversion model (DEC-20, RULE-UOM).

Stock is Nos (pieces); buying, selling and prices are Dozen.
1 Dozen = 12 Nos (PCS_PER_DOZEN). Floats and bools are rejected.

RULE-UOM 2: sales and purchases are entered in *whole* dozens.
``is_whole_dozen`` is True only for integer Dozen values.
``dozen_has_whole_pieces`` is True when the Dozen value maps to whole pieces
(e.g. 2.5 Dozen = 30 pieces).
"""

from decimal import Decimal

import pytest

from rules_engine.units import (
    PCS_PER_DOZEN,
    UomError,
    dozen_has_whole_pieces,
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
        (0, 0),
    ],
)
def test_dozen_to_pieces_accepts_int_str_decimal(
    dozens: Decimal | int | str, expected_pieces: int
) -> None:
    assert dozen_to_pieces(dozens) == expected_pieces


def test_dozen_to_pieces_rejects_non_whole_piece_result() -> None:
    """0.1 Dozen = 1.2 pieces, which is not whole -> UomError."""
    with pytest.raises(UomError):
        dozen_to_pieces(Decimal("0.1"))


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
    assert pieces_to_dozen(0) == Decimal("0")


# -- is_whole_dozen (RULE-UOM 2) ---------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        1,
        2,
        "3",
        Decimal("3.0"),
        0,
    ],
)
def test_is_whole_dozen_true(value: Decimal | int | str) -> None:
    """Integer Dozen values are whole dozens."""
    assert is_whole_dozen(value) is True


@pytest.mark.parametrize(
    "value",
    [
        Decimal("2.5"),
        Decimal("0.5"),
        "0.1",
    ],
)
def test_is_whole_dozen_false(value: Decimal | int | str) -> None:
    """Non-integer Dozen values are not whole dozens (RULE-UOM 2)."""
    assert is_whole_dozen(value) is False


# -- dozen_has_whole_pieces ---------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        Decimal("2.5"),  # 30 pieces
        Decimal("0.5"),  # 6 pieces
        Decimal("1") / 3,  # 4 pieces
        1,  # 12 pieces
    ],
)
def test_dozen_has_whole_pieces_true(value: Decimal | int | str) -> None:
    """These Dozen values map to a whole number of pieces."""
    assert dozen_has_whole_pieces(value) is True


@pytest.mark.parametrize(
    "value",
    [
        Decimal("0.1"),  # 1.2 pieces
        Decimal("0.3"),  # 3.6 pieces
        Decimal("1") / 7,  # ~1.714 pieces
    ],
)
def test_dozen_has_whole_pieces_false(value: Decimal | int | str) -> None:
    """These Dozen values do not map to a whole number of pieces."""
    assert dozen_has_whole_pieces(value) is False


# -- round-trip ---------------------------------------------------------------


@pytest.mark.parametrize("pieces", [1, 7, 12, 13, 18, 24])
def test_round_trip_dozen_to_pieces_to_dozen(pieces: int) -> None:
    """dozen_to_pieces(pieces_to_dozen(n)) == n for whole-piece counts."""
    assert dozen_to_pieces(pieces_to_dozen(pieces)) == pieces


# -- rejection cases ----------------------------------------------------------
# All four public functions go through _as_decimal, which rejects floats,
# bools, non-finite values, negatives and invalid strings.


@pytest.mark.parametrize(
    "fn",
    [dozen_to_pieces, pieces_to_dozen, is_whole_dozen, dozen_has_whole_pieces],
    ids=["d2p", "p2d", "iwd", "dwhp"],
)
class TestRejections:
    """Every public function must reject the same bad inputs."""

    def test_rejects_float(self, fn) -> None:
        with pytest.raises(TypeError):
            fn(1.5)  # type: ignore[arg-type]

    def test_rejects_bool_true(self, fn) -> None:
        with pytest.raises(TypeError):
            fn(True)  # type: ignore[arg-type]

    def test_rejects_bool_false(self, fn) -> None:
        with pytest.raises(TypeError):
            fn(False)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "bad",
        [
            -1,
            "-1",
            Decimal("-1"),
        ],
        ids=["neg-int", "neg-str", "neg-decimal"],
    )
    def test_rejects_negative(self, fn, bad: Decimal | int | str) -> None:
        with pytest.raises(UomError):
            fn(bad)

    @pytest.mark.parametrize(
        "bad",
        ["NaN", "sNaN", "Infinity", "-Infinity"],
    )
    def test_rejects_non_finite(self, fn, bad: str) -> None:
        with pytest.raises(UomError):
            fn(bad)

    @pytest.mark.parametrize(
        "bad",
        ["not-a-number", "", "abc"],
    )
    def test_rejects_invalid_string(self, fn, bad: str) -> None:
        with pytest.raises(UomError):
            fn(bad)
