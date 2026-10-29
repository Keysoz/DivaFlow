"""Local API: store gateway and Ops/POS API (TASK-E-12 skeleton).

The only component that talks to ERPNext. Every endpoint except /health requires
a bearer token; POS Next talks to ERPNext directly on the store LAN.
"""

from fastapi import Depends, FastAPI, HTTPException

from erpnext_adapter import ErpNextClient
from local_api.auth import require_token
from local_api.deps import get_client
from local_api.models import (
    BarcodeCreated,
    BarcodeInfo,
    BarcodeRequest,
    CounterRequest,
    CounterResponse,
    Health,
    ItemDetail,
    ItemResponse,
    ItemSummary,
    LabelResponse,
)
from rules_engine import (
    BarcodeError,
    is_valid_ean13,
    next_internal_ean13,
    validate_discount,
    validate_moq,
)

app = FastAPI(title="Diva Local API")


@app.get("/health")
def health() -> Health:
    """Report that the service is up."""
    return Health(status="ok")


@app.get("/api/items/by-barcode/{barcode}", dependencies=[Depends(require_token)])
def item_by_barcode(barcode: str, client: ErpNextClient = Depends(get_client)) -> ItemResponse:
    """Look up an item by barcode, with its per-Dozen price and stock."""
    item = client.get_item_by_barcode(barcode)
    if item is None:
        raise HTTPException(status_code=404, detail=f"no item for barcode {barcode}")
    item_code = str(item["item_code"])
    rate = client.get_price_list_rate(item_code, "Standard Selling", "Dozen")
    stock = client.get_bin(item_code)
    return ItemResponse(
        item_code=item_code,
        item_name=str(item.get("item_name", "")),
        stock_uom=str(item.get("stock_uom", "Nos")),
        barcode_uom=str(item["barcode_uom"]) if item.get("barcode_uom") else None,
        price_dozen=None if rate is None else str(rate),
        actual_qty=str(stock.get("actual_qty", 0)),
        reserved_qty=str(stock.get("reserved_qty", 0)),
    )


def _prices_for(client: ErpNextClient, item_code: str) -> dict[str, str | None]:
    prices = client.get_item_prices([item_code]).get(item_code, {})
    return {
        "price_dozen": str(prices["Dozen"]) if "Dozen" in prices else None,
        "price_nos": str(prices["Nos"]) if "Nos" in prices else None,
    }


def _stock_for(client: ErpNextClient, item_code: str) -> dict[str, str]:
    stock = client.get_bins([item_code]).get(item_code, {})
    return {
        "actual_qty": str(stock.get("actual_qty", 0)),
        "reserved_qty": str(stock.get("reserved_qty", 0)),
    }


@app.get("/api/items", dependencies=[Depends(require_token)])
def list_items(
    search: str | None = None,
    limit: int = 50,
    client: ErpNextClient = Depends(get_client),
) -> list[ItemSummary]:
    """List active items for the Ops Items screen (TASK-E-13)."""
    limit = max(1, min(limit, 100))
    items = client.get_items(search=search, limit=limit)
    codes = [str(item.get("item_code") or item.get("name")) for item in items]
    prices = client.get_item_prices(codes)
    bins = client.get_bins(codes)
    result: list[ItemSummary] = []
    for item in items:
        code = str(item.get("item_code") or item.get("name"))
        item_prices = prices.get(code, {})
        stock = bins.get(code, {})
        result.append(
            ItemSummary(
                item_code=code,
                item_name=str(item.get("item_name") or code),
                item_group=str(item.get("item_group") or ""),
                stock_uom=str(item.get("stock_uom") or "Nos"),
                is_stock_item=bool(item.get("is_stock_item", 1)),
                price_dozen=str(item_prices["Dozen"]) if "Dozen" in item_prices else None,
                price_nos=str(item_prices["Nos"]) if "Nos" in item_prices else None,
                actual_qty=str(stock.get("actual_qty", 0)),
                reserved_qty=str(stock.get("reserved_qty", 0)),
            )
        )
    return result


@app.get("/api/items/{item_code}", dependencies=[Depends(require_token)])
def get_item(item_code: str, client: ErpNextClient = Depends(get_client)) -> ItemDetail:
    """Return one item with barcodes, prices and stock."""
    try:
        item = client.get_item(item_code)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"item not found: {item_code}") from exc
    barcodes = [
        BarcodeInfo(barcode=str(row.get("barcode")), uom=str(row.get("uom") or ""))
        for row in client.get_barcodes(item_code)
        if row.get("barcode")
    ]
    prices = _prices_for(client, item_code)
    stock = _stock_for(client, item_code)
    return ItemDetail(
        item_code=item_code,
        item_name=str(item.get("item_name") or item_code),
        item_group=str(item.get("item_group") or ""),
        stock_uom=str(item.get("stock_uom") or "Nos"),
        is_stock_item=bool(item.get("is_stock_item", 1)),
        has_batch_no=bool(item.get("has_batch_no", 0)),
        has_serial_no=bool(item.get("has_serial_no", 0)),
        description=str(item.get("description") or ""),
        barcodes=barcodes,
        price_dozen=prices["price_dozen"],
        price_nos=prices["price_nos"],
        actual_qty=stock["actual_qty"],
        reserved_qty=stock["reserved_qty"],
    )


@app.post(
    "/api/items/{item_code}/barcodes",
    status_code=201,
    dependencies=[Depends(require_token)],
)
def add_item_barcode(
    item_code: str,
    request: BarcodeRequest,
    client: ErpNextClient = Depends(get_client),
) -> BarcodeCreated:
    """Add a barcode to an item, generating an internal EAN-13 when blank."""
    try:
        client.get_item(item_code)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"item not found: {item_code}") from exc

    uom = request.uom.strip()
    if not uom:
        raise HTTPException(status_code=422, detail="uom is required")

    barcode = (request.barcode or "").strip()
    generated = not barcode
    if barcode:
        if not is_valid_ean13(barcode):
            raise HTTPException(status_code=422, detail="barcode must be a valid EAN-13")
    else:
        try:
            barcode = next_internal_ean13(client.get_internal_barcodes(), prefix=20)
        except BarcodeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    existing = client.get_item_by_barcode(barcode)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"barcode already used: {barcode}")

    try:
        client.add_item_barcode(item_code, barcode, uom)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return BarcodeCreated(barcode=barcode, uom=uom, generated=generated)


@app.get("/api/labels", dependencies=[Depends(require_token)])
def label_data(
    item_code: str,
    uom: str = "Dozen",
    copies: int = 1,
    client: ErpNextClient = Depends(get_client),
) -> LabelResponse:
    """Return the data needed to draw one EAN-13 label (Tauri-free, app-drawn)."""
    copies = max(1, min(copies, 100))
    try:
        item = client.get_item(item_code)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"item not found: {item_code}") from exc
    barcodes = [
        row
        for row in client.get_barcodes(item_code)
        if str(row.get("uom")) == uom and row.get("barcode")
    ]
    if not barcodes:
        raise HTTPException(status_code=404, detail=f"no {uom} barcode for {item_code}")
    barcode = str(barcodes[0]["barcode"])
    price = client.get_price_list_rate(item_code, "Standard Selling", uom)
    return LabelResponse(
        item_code=item_code,
        item_name=str(item.get("item_name") or item_code),
        uom=uom,
        barcode=barcode,
        price=None if price is None else str(price),
        copies=copies,
        ean13=is_valid_ean13(barcode),
    )


@app.post("/api/rules/counter/evaluate", dependencies=[Depends(require_token)])
def evaluate_counter(request: CounterRequest) -> CounterResponse:
    """Run the counter rules (MOQ + effective discount) for the provided lines.

    TODO(TASK-E-14a): re-check price_list_rate/net_rate against the server price list
    (diva_guard owns the enforced check); this endpoint is advisory for the UI.
    """
    violations: list[dict[str, object]] = []
    audits: list[dict[str, object]] = []
    requires_manager = False
    for line in request.lines:
        violations.extend(validate_moq(line.qty_dozens, line.min_qty, line.step))
        discount = validate_discount(line.price_list_rate, line.net_rate)
        violations.extend(discount["violations"])  # type: ignore[arg-type]
        audits.append(discount["audit"])  # type: ignore[arg-type]
        requires_manager = requires_manager or bool(discount["requires_manager"])
    if request.role == "cashier" and requires_manager:
        violations.append(
            {
                "rule": "discount_manager_required",
                "message": "a manager PIN is required for this discount",
            }
        )
    return CounterResponse(
        ok=not violations,
        requires_manager=requires_manager,
        violations=violations,
        audits=audits,
    )
