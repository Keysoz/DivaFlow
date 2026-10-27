"""RULE-MIN: chat-order minimum (applies to chat orders only, DEC-07)."""

from decimal import Decimal

from rules_engine.values import quantize_money, to_decimal

DEFAULT_MIN_TOTAL_EGP = Decimal("3000")


def validate_min_order(
    goods_subtotal: Decimal | int | str,
    minimum: Decimal | int | str = DEFAULT_MIN_TOTAL_EGP,
) -> list[dict[str, object]]:
    """Return a structured violation when the goods subtotal is below the minimum."""
    subtotal = quantize_money(to_decimal(goods_subtotal))
    required = quantize_money(to_decimal(minimum))
    if subtotal >= required:
        return []
    return [
        {
            "rule": "min_total",
            "required": str(required),
            "current": str(subtotal),
            "gap": str(required - subtotal),
        }
    ]
