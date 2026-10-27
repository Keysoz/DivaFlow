"""Tests for the rules engine: MOQ, discount, min order, and to_decimal (TASK-E-12)."""

from decimal import Decimal

import pytest

from rules_engine import (
    effective_discount_percent,
    to_decimal,
    validate_discount,
    validate_min_order,
    validate_moq,
)


class TestToDecimal:
    """to_decimal rejects float/bool/non-finite and accepts Decimal/int/str."""

    def test_float_rejected(self):
        with pytest.raises(TypeError, match="floats are not allowed"):
            to_decimal(1.5)

    def test_bool_rejected(self):
        with pytest.raises(TypeError, match="a boolean is not a number"):
            to_decimal(True)

    def test_nan_rejected(self):
        with pytest.raises(ValueError, match="the value must be finite"):
            to_decimal(Decimal("nan"))

    def test_inf_rejected(self):
        with pytest.raises(ValueError, match="the value must be finite"):
            to_decimal(Decimal("inf"))

    def test_negative_inf_rejected(self):
        with pytest.raises(ValueError, match="the value must be finite"):
            to_decimal(Decimal("-inf"))

    def test_decimal_accepted(self):
        assert to_decimal(Decimal("1.5")) == Decimal("1.5")

    def test_int_accepted(self):
        assert to_decimal(42) == Decimal("42")

    def test_str_accepted(self):
        assert to_decimal("3.14") == Decimal("3.14")

    def test_negative_decimal_accepted(self):
        assert to_decimal(Decimal("-10")) == Decimal("-10")

    def test_zero_accepted(self):
        assert to_decimal(0) == Decimal("0")


class TestValidateMOQ:
    """validate_moq checks minimum quantity and step in Dozen."""

    def test_below_minimum_with_gap(self):
        violations = validate_moq(qty_dozens=2, min_qty=5, step=0)
        assert len(violations) == 1
        assert violations[0]["rule"] == "moq_min"
        assert violations[0]["required"] == "5"
        assert violations[0]["current"] == "2"
        assert violations[0]["gap"] == "3"

    def test_step_violation_with_next(self):
        violations = validate_moq(qty_dozens=3, min_qty=0, step=5)
        assert len(violations) == 1
        assert violations[0]["rule"] == "moq_step"
        assert violations[0]["step"] == "5"
        assert violations[0]["current"] == "3"
        assert violations[0]["next"] == "5"

    def test_zero_quantity(self):
        violations = validate_moq(qty_dozens=0, min_qty=0, step=0)
        assert len(violations) == 1
        assert violations[0]["rule"] == "moq_qty"
        assert violations[0]["current"] == "0"

    def test_negative_quantity(self):
        violations = validate_moq(qty_dozens=-1, min_qty=0, step=0)
        assert len(violations) == 1
        assert violations[0]["rule"] == "moq_qty"
        assert violations[0]["current"] == "-1"

    def test_ok_case(self):
        violations = validate_moq(qty_dozens=10, min_qty=5, step=5)
        assert violations == []

    def test_both_min_and_step_violations(self):
        violations = validate_moq(qty_dozens=2, min_qty=5, step=3)
        assert len(violations) == 2
        assert violations[0]["rule"] == "moq_min"
        assert violations[1]["rule"] == "moq_step"
        assert violations[1]["next"] == "3"

    def test_exact_minimum_ok(self):
        violations = validate_moq(qty_dozens=5, min_qty=5, step=0)
        assert violations == []

    def test_exact_step_multiple_ok(self):
        violations = validate_moq(qty_dozens=15, min_qty=0, step=5)
        assert violations == []


class TestEffectiveDiscountPercent:
    """effective_discount_percent calculates discount percentage."""

    def test_no_discount(self):
        assert effective_discount_percent(100, 100) == Decimal("0")

    def test_full_discount(self):
        assert effective_discount_percent(100, 0) == Decimal("100")

    def test_partial_discount(self):
        assert effective_discount_percent(100, 80) == Decimal("20")

    def test_half_discount(self):
        assert effective_discount_percent(Decimal("1000"), Decimal("500")) == Decimal("50")

    def test_price_increase_negative_discount(self):
        # net > price_list -> negative discount (price increase)
        result = effective_discount_percent(100, 110)
        assert result == Decimal("-10")

    def test_zero_price_raises(self):
        with pytest.raises(ValueError, match="price_list_rate must be positive"):
            effective_discount_percent(0, 50)

    def test_negative_price_raises(self):
        with pytest.raises(ValueError, match="price_list_rate must be positive"):
            effective_discount_percent(-100, 50)

    def test_negative_net_raises(self):
        with pytest.raises(ValueError, match="net_rate cannot be negative"):
            effective_discount_percent(100, -10)


class TestValidateDiscount:
    """validate_discount checks discount against role limits."""

    def test_zero_discount_ok(self):
        result = validate_discount(100, 100)
        assert result["ok"] is True
        assert result["discount_percent"] == "0.00"
        assert result["requires_manager"] is False
        assert result["violations"] == []

    def test_discount_below_cashier_limit_ok(self):
        result = validate_discount(1000, Decimal("951"))  # 4.9%
        assert result["ok"] is True
        assert result["discount_percent"] == "4.90"
        assert result["requires_manager"] is False

    def test_discount_at_cashier_limit_ok(self):
        result = validate_discount(1000, 950)  # 5%
        assert result["ok"] is True
        assert result["discount_percent"] == "5.00"
        assert result["requires_manager"] is False

    def test_discount_above_cashier_requires_manager(self):
        result = validate_discount(1000, 930)  # 7%
        assert result["ok"] is True
        assert result["discount_percent"] == "7.00"
        assert result["requires_manager"] is True
        assert result["violations"] == []

    def test_discount_at_manager_limit_ok(self):
        result = validate_discount(1000, 850)  # 15%
        assert result["ok"] is True
        assert result["discount_percent"] == "15.00"
        assert result["requires_manager"] is True

    def test_discount_above_manager_limit_violation(self):
        result = validate_discount(1000, 849)  # 15.1%
        assert result["ok"] is False
        assert result["discount_percent"] == "15.10"
        assert result["requires_manager"] is False
        assert len(result["violations"]) == 1
        assert result["violations"][0]["rule"] == "discount_limit"
        assert result["violations"][0]["limit"] == "15"
        assert result["violations"][0]["current"] == "15.10"

    def test_discount_twenty_percent_violation(self):
        result = validate_discount(100, 80)  # 20%
        assert result["ok"] is False
        assert result["discount_percent"] == "20.00"
        assert len(result["violations"]) == 1
        assert result["violations"][0]["rule"] == "discount_limit"

    def test_price_increase_violation(self):
        result = validate_discount(100, 110)  # -10% discount (price increase)
        assert result["ok"] is False
        assert len(result["violations"]) == 1
        assert result["violations"][0]["rule"] == "discount_negative"
        assert result["violations"][0]["current"] == "-10.00"

    def test_float_rejected(self):
        with pytest.raises(TypeError, match="floats are not allowed"):
            validate_discount(100.0, 90.0)

    def test_audit_record_present(self):
        result = validate_discount(1000, 930)
        assert "audit" in result
        audit = result["audit"]
        assert audit["rule"] == "discount_limit"
        assert audit["price_list_rate"] == "1000.00"
        assert audit["net_rate"] == "930.00"
        assert audit["discount_percent"] == "7.00"
        assert audit["requires_manager"] is True
        assert audit["approved_by"] is None


class TestValidateMinOrder:
    """validate_min_order checks minimum order total."""

    def test_below_minimum_with_gap(self):
        violations = validate_min_order(2550, minimum=3000)
        assert len(violations) == 1
        assert violations[0]["rule"] == "min_total"
        assert violations[0]["required"] == "3000.00"
        assert violations[0]["current"] == "2550.00"
        assert violations[0]["gap"] == "450.00"

    def test_at_minimum_ok(self):
        violations = validate_min_order(3000, minimum=3000)
        assert violations == []

    def test_above_minimum_ok(self):
        violations = validate_min_order(3500, minimum=3000)
        assert violations == []

    def test_default_minimum(self):
        # Default minimum is 3000
        violations = validate_min_order(2000)
        assert len(violations) == 1
        assert violations[0]["required"] == "3000.00"
        assert violations[0]["gap"] == "1000.00"

    def test_zero_subtotal_violation(self):
        violations = validate_min_order(0, minimum=3000)
        assert len(violations) == 1
        assert violations[0]["gap"] == "3000.00"
