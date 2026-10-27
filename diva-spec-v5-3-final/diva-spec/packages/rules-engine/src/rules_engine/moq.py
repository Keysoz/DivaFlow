"""RULE-MOQ: minimum quantity and step, expressed in Dozen (DEC-07)."""

from decimal import Decimal

from rules_engine.values import to_decimal


def validate_moq(
    qty_dozens: Decimal | int | str,
    min_qty: Decimal | int | str = 0,
    step: Decimal | int | str = 0,
) -> list[dict[str, object]]:
    """Return structured violations for a line quantity in Dozen (empty means OK)."""
    qty = to_decimal(qty_dozens)
    minimum = to_decimal(min_qty)
    increment = to_decimal(step)
    violations: list[dict[str, object]] = []

    if qty <= 0:
        violations.append(
            {"rule": "moq_qty", "current": str(qty), "message": "quantity must be positive"}
        )
        return violations
    if minimum > 0 and qty < minimum:
        violations.append(
            {
                "rule": "moq_min",
                "required": str(minimum),
                "current": str(qty),
                "gap": str(minimum - qty),
            }
        )
    if increment > 0 and qty % increment != 0:
        next_qty = (qty // increment + 1) * increment
        violations.append(
            {
                "rule": "moq_step",
                "step": str(increment),
                "current": str(qty),
                "next": str(next_qty),
            }
        )
    return violations
