"""Unit conversion for the Dozen/Nos stock model (DEC-20, RULE-UOM).

Stock is counted in Nos (pieces). Buying, selling and prices are in Dozen
(1 Dozen = 12 Nos, DEC-20). Never assume a quantity is in pieces without
checking its UOM.
"""

from decimal import Decimal, InvalidOperation

PCS_PER_DOZEN = 12


class UomError(ValueError):
    """A quantity cannot be converted between Dozen and Nos."""


def dozen_to_pieces(dozens: Decimal | int | str) -> int:
    """Return whole pieces for a quantity given in Dozen."""
    value = _as_decimal(dozens)
    pieces = value * PCS_PER_DOZEN
    if pieces != pieces.to_integral_value():
        raise UomError(f"{value} Dozen is not a whole number of pieces")
    return int(pieces)


def pieces_to_dozen(pieces: Decimal | int | str) -> Decimal:
    """Return the exact Dozen value for a quantity given in pieces."""
    return _as_decimal(pieces) / PCS_PER_DOZEN


def is_whole_dozen(dozens: Decimal | int | str) -> bool:
    """Say whether a Dozen quantity is a whole number of pieces."""
    value = _as_decimal(dozens) * PCS_PER_DOZEN
    return value == value.to_integral_value()


def _as_decimal(value: Decimal | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise TypeError("a boolean is not a quantity")
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        try:
            return Decimal(value)
        except InvalidOperation as exc:
            raise UomError(f"{value!r} is not a decimal quantity") from exc
    raise TypeError("quantities must be Decimal, int or str, never float")
