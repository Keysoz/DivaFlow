"""Shared numeric helpers for the rules engine (Decimal only, never float)."""

from decimal import Decimal, InvalidOperation

FloatLike = float  # annotation only; floats are rejected at runtime


def to_decimal(value: Decimal | int | str) -> Decimal:
    """Convert a quantity or money value to Decimal; reject floats and non-finite values."""
    if isinstance(value, bool):
        raise TypeError("a boolean is not a number")
    if isinstance(value, float):
        raise TypeError("floats are not allowed; use Decimal, int or str")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{value!r} is not a decimal number") from exc
    if not result.is_finite():
        raise ValueError("the value must be finite")
    return result


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))
