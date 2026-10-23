# 03 Domain and Data

## 1. Ownership
| Entity | Master | Replicated to |
|---|---|---|
| Item, SKU, barcodes, UOM, pack, batch/expiry | ERPNext | Cloud cache (read-only) |
| Stock, reservations | ERPNext | Cloud cache |
| Price lists, tiers, quantity breaks | ERPNext | Cloud cache |
| Customer business record, credit limit, payment terms template | ERPNext | Cloud cache |
| `product_rules` (MOQ, step, max, scope, publish status) as `Diva Product Rule` | ERPNext (doctype owned by `diva_guard`) | Cloud cache via change feed |
| Reseller approval, tier mapping, channel identities, payment policy | cloud-api DB | ERPNext Customer created on approval |
| Conversations and messages | Chatwoot + cloud-api | none |
| Carts, draft orders, order/payment/shipment state | cloud-api DB | ERPNext Sales Order holds the commercial order |
| Sales Order, Delivery Note, Sales Invoice, Payment Entry | ERPNext | cloud shows status |
| Payment proofs and verification ledger | cloud-api DB | draft Payment Entry in ERPNext |
| Held counter sales, shifts, price/discount override audit | local-api DB | summaries to cloud |
| Shipments, tracking | Bosta, mirrored in cloud-api | |
| Posts and publish status | cloud-api DB | |
| Price observations | cloud-api DB | |
| Settings and rule versions | cloud-api DB (master) | local-api (replicated) |

No custom fields in ERPNext (DEC-04). The order reference lives in the standard `po_no` field.

## 2. Core tables (cloud-api)
`resellers`, `reseller_identities`, `conversations`, `messages`, `media_assets`, `carts`, `cart_lines`, `orders`, `order_lines`, `order_events`, `payment_proofs`, `payment_ledger`, `shipments`, `shipment_events`, `outbox`, `inbound_events`, `dead_letters`, `posts`, `post_targets`, `price_observations`, `settings_versions`, `audit_log`, `catalog_cache_*`.

## 3. Core tables (local-api)
`override_audit` (mirror), `barcode_cache`, `label_jobs`, `sync_cursor`, `audit_log`. Held sales and shifts live in POSNext and ERPNext POS entries.

## 4. Key fields
- `orders`: `id` (ULID, also `external_ref` as `DS-<ULID>`), `channel` (counter/chat/miniapp), `reseller_id`, `order_state`, `payment_state`, `shipment_state`, `goods_subtotal`, `discount_total`, `shipping_fee`, `grand_total`, `rule_set_version`, `price_snapshot`, `erp_sales_order`, `created_by`, timestamps.
- `payment_ledger` (append-only): `order_id`, `kind` (proof/deposit/full/cod_collected/cod_remitted/refund), `amount`, `mode`, `reference`, `proof_id`, `actor`, `verified_by`, `verified_at`, `note`.
- Held sales are POSNext draft invoices (no separate table).
- `product_rules`: `item_code`, `min_qty`, `qty_step`, `max_qty`, `moq_scope` (family/variant), `publish_status`.

## 5. Identifier rules
ULIDs for application IDs. Never derive IDs from timestamps. ERPNext names are stored, never constructed. Barcodes are internal EAN-13 numbers in GS1's in-store range (prefix 20–29), as the legacy app already generates; **existing barcodes are kept**. New items get an internal EAN-13 as item code and barcode (DEC-32). Supplier EAN codes are extra barcodes; pack barcodes use UOM conversion.

## 6a. Names and languages
`item_name` is the Arabic name. English name, bilingual descriptions and keywords are fields of the `Diva Product Rule` doctype (`name_en`, `description_ar`, `description_en`, `keywords`). Resellers store `preferred_language` (`ar` or `en`). See `19`.

## 6. Units
Stock in Nos (piece); trading and prices in Dozen (12). `product_rules` quantities are in dozens. Store the UOM next to every quantity in APIs and events.

## 7. Domain events (outbox)
`order.created`, `order.confirmed`, `order.expired`, `order.cancelled`, `payment.proof_received`, `payment.verified`, `payment.refund_requested`, `shipment.created`, `shipment.status_changed`, `catalog.changed`, `store.link_opened`, `store.link_closed`, `ai.handoff_requested`. Each event has an ID, version, timestamp and actor and is consumed idempotently.
