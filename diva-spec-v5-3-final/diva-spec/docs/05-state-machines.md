# 05 State Machines

Order, payment and shipment are separate state machines. Every transition is idempotent, logged with actor and timestamp, and rejected if illegal. Code lives in `cloud-api` with a transition guard that consults the matrix below.

## Order
`draft → validated → awaiting_shipping_quote → awaiting_confirmation → awaiting_deposit → confirmed → ready_for_dispatch → completed`, with `cancelled` and `expired` as exits. `awaiting_deposit` is skipped for `cod_allowed`.
- `validated`: rules engine passed.
- `awaiting_shipping_quote`: staff must set the fee (RULE-SHIP).
- `awaiting_confirmation`: final total sent; reseller must confirm.
- `awaiting_deposit`: the policy requires a deposit or prepayment that is not yet verified. **No stock is reserved.** Expires at the deposit deadline.
- `confirmed`: required payment verified (or COD policy); ERPNext Sales Order submitted with stock reservation.
- `ready_for_dispatch`: packed and scanned; Delivery Note and Sales Invoice created; the deposit advance is allocated to the invoice (DEC-46).
- `completed`: shipment delivered and balance zero (verified paid or COD remitted). A defect after completion uses the return flow with a credit note; orders are never reopened.
- `expired`: unpaid reservation window elapsed.

## Payment
`unpaid → proof_received → partially_paid → paid`; COD: `cod_pending → cod_collected → cod_remitted`; refunds: `refund_pending → partially_refunded → refunded`; `reconciliation_required` as an exception state.
- Only a `payment_reviewer` can move to `partially_paid` or `paid`.

## Shipment
`not_created → created → picked_up → in_transit → out_for_delivery → delivered`; failures: `delivery_failed → return_in_progress → returned`; `cancelled`; `reconciliation_required`.
- Creating a shipment requires order `confirmed` and (payment `paid`, or deposit met, or COD allowed) and all pack lines scanned (warning mode first, blocking later).

## Cross-state matrix
| Event | Order | Payment | Shipment |
|---|---|---|---|
| Reseller confirms (deposit policy) | awaiting_deposit | unpaid or proof_received | not_created |
| Reseller confirms (COD policy) | confirmed (reserved) | unpaid | not_created |
| Deposit verified | confirmed (reserved) | partially_paid | not_created |
| Packed and scanned | ready_for_dispatch | partially_paid or paid | not_created |
| Ready to ship | confirmed | paid, deposit met, or COD allowed | created |
| COD delivered | completed after remittance | cod_collected then cod_remitted | delivered |
| Delivery failed | confirmed | unchanged (COD back to cod_pending) | delivery_failed, return_in_progress, returned |
| Returned, prepaid | cancelled after stock returned in ERPNext | refund_pending then refunded | returned |
| Cancel before shipping | cancelled | refund_pending if anything was paid | not_created or cancelled |
| Deposit deadline passes | expired | unpaid | not_created |

## Counter hold (POSNext drafts, DEC-29)
`held → resumed → completed`, or `abandoned` after expiry (default 12 hours, configurable). A held sale is a POSNext draft invoice created through POSNext's draft flow. `docstatus = 0` alone never defines a held sale. Resuming a draft updates that same draft and never creates a second invoice. A resumed draft locks to the cashier to prevent concurrent edits.

## Shift (POSNext opening and closing entries)
`open → closing → closed`, with `variance_flagged` when counted cash differs from expected per payment mode. Opening records the float; closing records counts per mode and consolidates through the chosen POS path.

## Store link (cloud-api)
`store_online ⇄ store_offline` per `02-architecture.md` section 4.

## Conversation ownership
`ai ⇄ human`. Chatwoot assignee and status are the source of truth, mirrored by webhook with a version. The cloud re-reads ownership immediately before every AI send and discards the reply if a human took over.
