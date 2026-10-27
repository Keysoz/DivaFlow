"""RULE-DISC: effective discount against the price list, with role limits (DEC-13/DEC-50)."""

from decimal import Decimal

from rules_engine.values import quantize_money, to_decimal

CASHIER_LIMIT_PERCENT = Decimal("5")
MANAGER_LIMIT_PERCENT = Decimal("15")


def effective_discount_percent(
    price_list_rate: Decimal | int | str, net_rate: Decimal | int | str
) -> Decimal:
    """Discount as a percentage of the price-list rate, rounded to two decimals."""
    price = to_decimal(price_list_rate)
    net = to_decimal(net_rate)
    if price <= 0:
        raise ValueError("price_list_rate must be positive")
    if net < 0:
        raise ValueError("net_rate cannot be negative")
    return quantize_money((price - net) / price * Decimal("100"))


def validate_discount(
    price_list_rate: Decimal | int | str,
    net_rate: Decimal | int | str,
    cashier_limit: Decimal | int | str = CASHIER_LIMIT_PERCENT,
    manager_limit: Decimal | int | str = MANAGER_LIMIT_PERCENT,
) -> dict[str, object]:
    """Evaluate one line.

    Returns the effective discount, whether a manager must approve, any
    violations, and an audit record for the override ledger.
    """
    price = quantize_money(to_decimal(price_list_rate))
    net = quantize_money(to_decimal(net_rate))
    cashier = to_decimal(cashier_limit)
    manager = to_decimal(manager_limit)
    discount = effective_discount_percent(price, net)

    violations: list[dict[str, object]] = []
    requires_manager = False
    if net > price:
        violations.append(
            {
                "rule": "discount_negative",
                "current": str(discount),
                "message": "price is above the list",
            }
        )
    elif discount > manager:
        violations.append(
            {
                "rule": "discount_limit",
                "limit": str(manager),
                "current": str(discount),
                "message": "discount exceeds the manager limit",
            }
        )
    elif discount > cashier:
        requires_manager = True

    audit = {
        "rule": "discount_limit",
        "price_list_rate": str(price),
        "net_rate": str(net),
        "discount_percent": str(discount),
        "cashier_limit": str(cashier),
        "manager_limit": str(manager),
        "requires_manager": requires_manager,
        "actor": None,
        "reason": None,
        "amount": str(price - net),
        "approved_by": None,
    }
    return {
        "ok": not violations,
        "discount_percent": str(discount),
        "requires_manager": requires_manager,
        "violations": violations,
        "audit": audit,
    }
