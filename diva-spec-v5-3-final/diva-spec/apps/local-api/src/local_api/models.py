"""Request and response models for the local API (TASK-E-12)."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class Health(BaseModel):
    status: str


class ItemResponse(BaseModel):
    item_code: str
    item_name: str
    stock_uom: str
    barcode_uom: str | None = None
    price_dozen: str | None = None
    actual_qty: str = "0"
    reserved_qty: str = "0"


class CounterLine(BaseModel):
    item_code: str
    qty_dozens: Decimal
    min_qty: Decimal = Decimal("0")
    step: Decimal = Decimal("0")
    price_list_rate: Decimal
    net_rate: Decimal


class CounterRequest(BaseModel):
    # TODO(TASK-E-14a): the role must come from the authenticated principal, not the body.
    role: Literal["cashier", "manager"] = "cashier"
    lines: list[CounterLine] = Field(min_length=1)


class CounterResponse(BaseModel):
    ok: bool
    requires_manager: bool
    violations: list[dict[str, object]]
    audits: list[dict[str, object]]
