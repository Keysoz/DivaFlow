# 06 Core Modules

Each module lists purpose, interfaces, behavior and acceptance criteria (AC).

## M-GATEWAY (`apps/local-api`, `packages/erpnext-adapter`)
**Purpose:** the only code that talks to ERPNext; the cloud's safe door to the store.
- Typed ERPNext adapter using documented REST resources and whitelisted methods only. Retries with backoff. Reconcile-before-retry using `po_no`.
- Gateway endpoints per `02-architecture.md` section 3, with idempotency keys, request IDs, structured errors.
- Single writer per `external_ref` (unique constraint plus per-key lock).
- Per-user ERPNext API credentials held encrypted (DEC-09). Fallback integration user with actor in remarks.
- Totals, taxes and rounding always from ERPNext responses.
- Contract test suite against staging ERPNext: nightly and before every ERPNext upgrade; failure blocks the upgrade.
**AC:** duplicate `POST /gateway/orders` with the same key returns the same Sales Order; a simulated ERPNext timeout after a successful create results in exactly one Sales Order; unauthenticated calls are rejected.

## M-CATALOG-SYNC
**Purpose:** keep the cloud cache current.
- Change feed with cursor from local-api; nightly full reconcile; drift report.
- Replicates items, barcodes, UOM, pack, batch/expiry flags, prices, stock by sellable warehouse, customers, `product_rules`.
**AC:** a product edited in ERPNext appears in the cloud cache within 60 seconds; reconcile reports zero drift on a clean run.

## M-RULES (`packages/rules-engine`)
**Purpose:** all rules in `04-business-rules.md`.
- Pure functions, no I/O, Decimal money, 100% branch coverage on rule modules.
- Inputs: cart or sale, price/stock facts, settings version, actor role. Outputs: validation result or structured errors, suggested basket additions.
**AC:** TEST-01 to TEST-12 in `10-quality-security.md` pass.

## M-ORDER (`apps/cloud-api`)
**Purpose:** chat and Mini App order lifecycle.
- Cart and draft API; staff order entry (SKU or scanned barcode) through the same API.
- State machines and transition guard (`05-state-machines.md`).
- Flow: draft → validate (rules + gateway availability and prices) → shipping quote by staff → final total to reseller → reseller confirms → if the policy needs a deposit, state `awaiting_deposit` (no stock held) → reviewer verifies the deposit → gateway submits the Sales Order with reservation → packing → `ready_for_dispatch` creates the Delivery Note and Sales Invoice and allocates the deposit advance.
- Reservation expiry job. Price snapshot at confirmation.
- Store-link circuit breaker blocks creation when `store_offline`.
**AC:** a 2,999 EGP chat basket is rejected with the gap; 3,000 passes; counter 2,999 sale is allowed; expired reservation releases stock; link-down state prevents new orders and shows the notice.

## M-PAYMENT
**Purpose:** proofs, human verification, ledger, draft Payment Entry.
- Proof intake (staff upload first, channel media later). Flags for mismatch, reused reference, duplicate hash.
- Verification action restricted to `payment_reviewer`; MFA required.
- Append-only ledger; refund entries; COD events from Bosta.
- Gateway creates a draft Payment Entry after verification, as a **customer advance against the Sales Order** for deposits; accounts submits it in Ops; the advance is allocated to the Sales Invoice at ready-for-dispatch. For suppliers in the China group, a guard rule rejects any mode except Bank Transfer.
**AC:** a customer message saying payment is done never changes payment state; verification writes ledger and draft Payment Entry exactly once on repeat calls.

## M-BOSTA
**Purpose:** shipping.
- Client for create delivery (COD amount), track, cancel, AWB, returns/exchanges. Staging environment in dev.
- Address normalizer to city/zone/district IDs with a confirmation step.
- Webhook receiver: verify secret, deduplicate, map to shipment states, notify the reseller.
- COD remittance reconciliation.
**AC:** duplicate Bosta webhooks send one notification; shipment creation is blocked until order and payment preconditions pass; address without resolved IDs cannot ship.

## M-NOTIFY
**Purpose:** outbound messages.
- Outbox consumer, template registry (WhatsApp approved templates), 24-hour window awareness, rate limits, dead-letter queue.
- Marketing messages only to opted-in resellers with a stored consent record.
**AC:** a message outside the window uses a template or is held for a human; failures retry with backoff, then dead-letter and alert.

## M-SETTINGS
**Purpose:** versioned configuration (RULE-RULESET) with UI in Control Room and replication to local-api.
**AC:** changing the minimum total creates a new version with an effective date; existing orders keep their recorded version.

## M-AUTH-AUDIT
**Purpose:** login, roles, MFA, audit.
- Email + password with MFA for owner and `payment_reviewer`. Role checks on the server. CSRF protection on session endpoints.
- Audit log for every sensitive action (RULE-AUDIT), searchable in Control Room.
**AC:** a cashier cannot approve a discount above 5% or open payment verification; every override appears in the audit log.
