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


class BarcodeInfo(BaseModel):
    barcode: str
    uom: str


class ItemSummary(BaseModel):
    item_code: str
    item_name: str
    item_group: str = ""
    stock_uom: str = "Nos"
    is_stock_item: bool = True
    price_dozen: str | None = None
    price_nos: str | None = None
    actual_qty: str = "0"
    reserved_qty: str = "0"


class ItemDetail(ItemSummary):
    has_batch_no: bool = False
    has_serial_no: bool = False
    description: str = ""
    barcodes: list[BarcodeInfo] = Field(default_factory=list)


class BarcodeRequest(BaseModel):
    barcode: str | None = None
    uom: str = Field(min_length=1)


class BarcodeCreated(BaseModel):
    barcode: str
    uom: str
    generated: bool


class LabelResponse(BaseModel):
    item_code: str
    item_name: str
    uom: str
    barcode: str
    price: str | None = None
    copies: int = 1
    ean13: bool = False
