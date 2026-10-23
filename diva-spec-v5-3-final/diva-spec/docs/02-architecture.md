# 02 Architecture

## 1. Topology (DEC-05: split deployment)

```
Resellers ─► WhatsApp / Instagram / Facebook ─► Chatwoot (cloud)
                                                   │ webhook
CLOUD NODE (VPS)                                   ▼
 cloud-api (FastAPI + workers) · Postgres+pgvector · Chatwoot · n8n
 Control Room · Mini App · Telegram admin bot · object storage
 AI orchestrator · content publisher · Bosta client · market-worker
            │  WireGuard tunnel (the Link), cloud ──► store only
            ▼
STORE NODE (private VM, LAN)
 local-api (gateway + Ops/POS API) · local Postgres · ops-pwa
 ERPNext 16 + MariaDB + Redis (reachable ONLY by local-api)
 Counter terminals (browser): scanner, receipt printer, label printer
```

The counter works whenever the store LAN works, even with no internet. Chat, AI and publishing need the internet.

## 2. Components
| Component | Node | Responsibility |
|---|---|---|
| `cloud-api` | Cloud | Conversations, resellers, carts, order state machines, payment ledger, Bosta, content, AI orchestration, Control Room API, Telegram bot, outbox and jobs |
| `local-api` | Store | **Gateway** for the cloud; ERPNext adapter; Ops API; item and barcode service; override audit mirror; barcode cache |
| POSNext | Store (inside ERPNext's bench) | Counter POS: scanning, drafts, shifts, payments, receipts. Talks to ERPNext directly on the LAN |
| `diva_guard` | Store (inside ERPNext) | Server-side validation hooks (MOQ, discount limits, price integrity, no counter credit) and the `Diva Product Rule` doctype |
| `ops-pwa` | Store (served by local-api) | Staff screens: Receive, Transfer, Count, Collect, Labels, Items, Pack |
| `control-room` | Cloud | Management dashboard |
| `mini-app` | Cloud | Reseller catalog and checkout |
| `rules-engine` | Both (shared package) | Pure business rules |
| Chatwoot | Cloud | Channel owner and shared inbox |
| n8n | Cloud | Schedules, briefs, alerts only |
| ERPNext | Store | Items, stock, prices, customers, Sales Orders, invoices, payments, accounting |

## 3. Gateway contract (cloud → local-api)
All calls carry an idempotency key, a request ID and a service token over the Link. Responses are typed. Endpoints (OpenAPI in `packages/contracts`):
- `GET /gateway/health`
- `GET /gateway/availability?skus=` returns available-to-promise per SKU
- `POST /gateway/orders` create-or-get a Sales Order by `external_ref` (stored in standard `po_no`)
- `POST /gateway/orders/{ref}/confirm` submit with stock reservation
- `POST /gateway/orders/{ref}/ready` create the Delivery Note and Sales Invoice and allocate the deposit advance
- `POST /gateway/orders/{ref}/release` cancel and release reservation
- `POST /gateway/payments/draft` create a draft Payment Entry
- `GET /gateway/changes?cursor=` change feed for items, prices, stock, barcodes, product rules, customers
- `POST /gateway/shipments/mark` record a shipment reference on the order

The cloud keeps a read-only cache built from the change feed (nightly full reconcile). The cache serves browsing and AI answers. **Every order, price and stock check that matters is revalidated through the gateway.**

## 4. Link-down behavior (DEC-06)
- The cloud pings `GET /gateway/health` every 15 s. After 3 failures (about 45 s) the circuit opens: state `store_offline`. After 3 consecutive successes it closes.
- While `store_offline`: no new orders, carts or confirmations are created. The AI and staff reply with the configured notice that ordering is paused briefly. Browsing answers may continue with a notice that prices and stock may be outdated. Payment proofs may still be received.
- The owner gets a Telegram alert on open and on close. The dashboard shows a banner and a list of conversations to follow up.
- Orders already created are reconciled by `external_ref` when the link returns. Never retry a gateway write without checking by `external_ref` first.
- Sample notice (ar): "الطلبات متوقفة مؤقتاً لعطل فني بسيط، وهنرجعلك أول ما يتحل."

## 5. Counter independence
Counter sales run on POSNext against ERPNext on the store LAN; `ops-pwa` talks only to `local-api`. Neither depends on the cloud. `product_rules` (MOQ, step, publish flags) are mastered in ERPNext as the `Diva Product Rule` doctype owned by `diva_guard`, and replicated to the cloud through the change feed, so MOQ is enforced at the counter even with no internet. Rule enforcement at the counter happens in `diva_guard` hooks at invoice validate and submit, so it cannot be bypassed from the browser.

## 6. Data flow summary
Items, stock, prices, barcodes: ERPNext → local-api → change feed → cloud cache. Orders: cloud → gateway → ERPNext. Counter sales: ops-pwa → local-api → ERPNext. Payments: proof in cloud → human verifies → draft Payment Entry via gateway → accounts submits.

## 7. Environments
`dev` (Docker Compose, both nodes, Postgres, a staging ERPNext copy), `staging` (mirrors production, test Meta/Bosta accounts), `prod`. Separate credentials per environment. Staging ERPNext holds realistic data.

## 8. Security boundaries
ERPNext private to the store LAN. The Link is the only path between nodes. Each staff member has an ERPNext user; `local-api` holds their API credentials encrypted and uses them for their actions (DEC-09). Fallback: integration user with the actor stamped in remarks. Webhooks verified by signature. Media in private object storage with signed, expiring URLs.

## 9. Resilience rules
Durable inbound events before processing. Transactional outbox for outgoing side effects. Dead-letter queue visible in the dashboard. Reconcile-before-retry for every external write. Idempotency keys on every command. Stale AI replies are discarded if a human took over during generation.
