"""Local API: store gateway and Ops/POS API (TASK-E-12 skeleton).

The only component that talks to ERPNext. Every endpoint except /health requires
a bearer token; POS Next talks to ERPNext directly on the store LAN.
"""

from fastapi import Depends, FastAPI, HTTPException

from erpnext_adapter import ErpNextClient
from local_api.auth import require_token
from local_api.deps import get_client
from local_api.models import (
    CounterRequest,
    CounterResponse,
    Health,
    ItemResponse,
)
from rules_engine import validate_discount, validate_moq

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
