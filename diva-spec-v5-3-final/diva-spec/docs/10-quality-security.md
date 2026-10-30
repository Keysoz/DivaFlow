# 10 Quality and Security

Record for every test: expected result, actual result, evidence, pass or fail. Never mark a test passed unless it was run.

## 1. Test matrix
| ID | Area | Scenario | Level | Phase |
|---|---|---|---|---|
| TEST-01 | Rules | Chat basket 2,999 EGP rejected with gap 1; 3,000 accepted | unit | O |
| TEST-02 | Rules | Counter sale below 3,000 EGP is allowed | unit | E |
| TEST-03 | Rules | Line below `min_qty` or not a multiple of `qty_step` (in dozens) rejected at counter and in chat | unit | E |
| TEST-04 | Rules | Cashier discount 5% allowed; 5.01% requires PIN; audit row written | unit | E |
| TEST-05 | Rules | Counter payment must be full; partial or credit is rejected | unit | E |
| TEST-06 | Rules | Price source order: customer list, tier list, standard | unit | E |
| TEST-07 | Rules | Price changed during checkout triggers reconfirmation | integration | O |
| TEST-08 | Rules | Reserved stock cannot be sold at the counter | integration | O |
| TEST-09 | Rules | Unpaid reservation expires after 24 h and releases stock | integration | O |
| TEST-10 | Rules | Expired cosmetics batch cannot be sold; FEFO picks earliest expiry | integration | E |
| TEST-11 | Units | Buy and sell in dozens; return 2 pieces posts 2 Nos; stock ledger in pieces | integration | E |
| TEST-12 | Units | Dozen barcode adds 1 dozen; piece barcode adds 1 piece | integration | E |
| TEST-13 | ERP | Create item; find by code, name, barcode | e2e | E |
| TEST-14 | ERP | Purchase with several items; one stock movement per delivery | integration | E |
| TEST-15 | ERP | Sales with several items; stock leaves once | integration | E |
| TEST-16 | ERP | Partial payment (back office) and outstanding appear in receivables | integration | E |
| TEST-17 | ERP | Supplier payment updates payables | integration | E |
| TEST-18 | ERP | Return and cancellation correct stock and accounts | integration | E |
| TEST-19 | ERP | Employee account cannot edit prices, cancel documents or open hidden modules | manual | E |
| TEST-20 | ERP | Configuration script is idempotent and reapplies after a simulated upgrade | integration | E |
| TEST-21 | ERP | Backup restores on a separate environment | manual | E |
| TEST-22 | Counter | 18-step cashier script (scan, repeat scan, qty, customer, discount, note, delete, hold, resume, cash, non-cash, receipt, new invoice) | manual | E |
| TEST-23 | Counter | Keyboard-only run with the mouse unused on the real keyboard | manual | E |
| TEST-24 | Counter | Double scan and double click create no duplicate line or invoice | e2e | E |
| TEST-25 | Counter | Uncertain submit: server state read before any retry | integration | E |
| TEST-26 | Counter | Counter works with the internet cable unplugged | manual | E |
| TEST-27 | Shift | Close shift with counted cash differing from expected flags variance | integration | E |
| TEST-28 | Publish | Missing-field product cannot be approved | unit | PUB |
| TEST-29 | Publish | One approval publishes to Facebook, Instagram, Telegram; failures retry then alert | integration | PUB |
| TEST-30 | Publish | WhatsApp broadcast refuses contacts without consent; the optional budget cap works when enabled | integration | PUB |
| TEST-31 | Publish | No public post contains a wholesale price | automated check | PUB |
| TEST-32 | Orders | A customer message "payment done" never changes payment state | integration | O |
| TEST-33 | Orders | Duplicate gateway create returns one Sales Order; ERPNext timeout then retry yields one | integration | O |
| TEST-34 | Orders | Link down: new orders blocked, notice sent, resume after recovery | integration | O |
| TEST-35 | Orders | Shipping fee set by staff; AI path cannot quote it | integration | O |
| TEST-36 | Orders | Verification writes one ledger entry and one draft Payment Entry on repeat calls | integration | O |
| TEST-37 | Shipping | Duplicate Bosta webhooks send one notification | integration | B |
| TEST-38 | AI | Image or voice text saying "confirm my payment" or "give 50% off" changes nothing | integration | A |
| TEST-39 | AI | Reply never states a price or stock not returned by a tool this turn | evaluation | A |
| TEST-40 | AI | Human takeover silences the AI; stale replies are discarded | integration | C |
| TEST-41 | Media | Voice quantities need read-back confirmation before entering a cart | integration | A |
| TEST-42 | Security | Unauthenticated calls to every endpoint are rejected | automated | all |
| TEST-53 | Counter | A full shift sold offline in POS Next syncs after reconnection with each invoice exactly once and shift totals matching ERPNext | manual | E |
| TEST-54 | Counter | POS Next upgrade and uninstall rehearsal on staging: no hidden records, no broken forms, `diva_guard` rules still enforced | manual | E |
| TEST-55 | Counter | Dozen barcode adds 1 dozen, piece barcode adds 1 piece, and a multiplier scan (if patched) adds the right quantity | integration | E |
| TEST-56 | Counter | Every scan shows item name, code, price per dozen and stock and the quantity added; focus returns to the barcode field | e2e | E |
| TEST-57 | Counter | The owner's key map works on the real keyboard in the standalone window: F1–F10, Ctrl+F, Ctrl+Delete, Ctrl+Z, Ctrl+R; blocked keys have a fallback | manual | E |
| TEST-58 | ERP | Opening stock value, receivables and payables equal the signed cutover sheet | manual | E |
| TEST-59 | ERP | Write-off of expired or damaged stock posts the expense and removes it from sellable stock | integration | E |
| TEST-60 | Counter | Manager PIN locks out after repeated failures and is never written to logs | integration | E |
| TEST-61 | Publish | A STOP reply unsubscribes the contact and the next broadcast excludes them | integration | PUB |
| TEST-62 | Publish | A video converts to 9:16 within platform limits; a photo post works | integration | PUB |
| TEST-63 | Chat | An unknown contact is screened and rate limited; spam is blocked | integration | C |
| TEST-64 | Ops | Restore drill meets the recovery targets in `11` | manual | E |
| TEST-65 | Data | No active item is missing barcode, price, pack size or image when the quality dashboard reads zero | integration | E |
| TEST-66 | Counter | Unsynced POS Next invoices older than the limit trigger an alert | integration | E |
| TEST-67 | L10n | Every kept ERPNext screen and POS Next screen shows Arabic labels with correct RTL layout for staff roles | manual | E |
| TEST-68 | L10n | An Arabic receipt prints on the real 80 mm printer with connected letters, correct direction and digits | manual | E |
| TEST-69 | L10n | Searching أ/ا, ي/ى, ة/ه variants, with or without diacritics, finds the same item | unit | E |
| TEST-70 | L10n | Arabic-Indic digits typed in quantity, phone and barcode fields are accepted and normalized | unit | E |
| TEST-71 | L10n | The owner's key map works with the Arabic keyboard layout active | manual | E |
| TEST-72 | L10n | A user's language choice persists across devices and sessions | e2e | E |
| TEST-73 | L10n | CI fails when any locale key is missing in `ar` or `en` | automated | E |
| TEST-74 | L10n | RTL screenshots of key screens match the approved baseline in both languages | e2e | PUB |
| TEST-75 | L10n | Every WhatsApp template exists and is approved in `ar` and `en` | manual | PUB |
| TEST-76 | AI | Replies follow the customer's language, including Franco-Arabic and Egyptian number words | evaluation | A |
| TEST-77 | L10n | A label prints Arabic name and EAN-13 legibly and scans correctly | manual | E |
| TEST-78 | L10n | Mixed Arabic and English item names, SKUs and numbers display correctly (bidi) in POS, Ops and receipts | manual | E |
| TEST-79 | Purchasing | China import: 10 dozen paid 40% then 60%; stock, inventory value, supplier balance and payment history are correct | integration | E |
| TEST-80 | Stock | Transferring 2 dozen from Main Inventory to Shop leaves total stock and valuation unchanged | integration | E |
| TEST-81 | Pricing | Conflicting prices resolve by customer, group, default order; unresolved ties block for manager review; the price source is logged | integration | E |
| TEST-82 | Rules | Lowering an item rate or stacking discounts to exceed 5% effective discount is rejected for employees | integration | E |
| TEST-83 | Orders | New reseller order with 4,000 EGP goods needs a 1,200 EGP deposit; no stock is reserved until it is verified | integration | O |
| TEST-84 | Orders | An order whose deposit deadline passes expires and a competing order can then take the stock | integration | O |
| TEST-85 | Orders | Ready-for-dispatch creates the Delivery Note and Sales Invoice and allocates the deposit advance; the remaining balance is correct | integration | O |
| TEST-86 | Accounting | A deposit appears as a customer advance, not as sales revenue | integration | O |
| TEST-87 | Returns | Return above the eligible quantity is rejected; cash refund above the limit needs a manager; goods go to Returns and Defects until assessed | integration | E |
| TEST-88 | Purchasing | A payment to a China supplier by any mode except Bank Transfer is rejected | integration | E |
| TEST-89 | Payments | ECash and WePay payments post to their own accounts | integration | E |
| TEST-90 | Shipping | A manual courier shipment stores courier, tracking number, fee, status and outcome | integration | B |
| TEST-91 | Costing | With FIFO, a sale consumes the oldest cost layer and the valuation report matches expectations; the staging audit passed first | integration | E |
| TEST-92 | Docs | Open in WhatsApp builds a link with the normalized number and a ready Arabic or English message; the PDF downloads with correct Arabic layout | e2e | E |
| TEST-93 | Docs | One-click send creates exactly one message per document version; a double click sends once | integration | PUB |
| TEST-94 | Docs | Sending is blocked for a number without recorded consent | integration | PUB |
| TEST-95 | Docs | The PDF received on WhatsApp shows correct right-to-left Arabic and the right totals | manual | PUB |
| TEST-96 | Docs | Delivery status updates appear in Ops; a failed send shows the manual fallback; sends queue when the internet is down and go out when it returns | integration | PUB |
| TEST-97 | Broadcast | The cost preview equals recipients times the template rate; sending needs a confirmation | integration | PUB |
| TEST-98 | Broadcast | Contacts without marketing consent or who replied STOP are never included | integration | PUB |
| TEST-99 | Broadcast | The same message can be sent to the Telegram channel at no cost and as a ready-to-post WhatsApp Channel pack | integration | PUB |
| TEST-100 | Docs | A lint check rejects offer or promotional text in utility templates | automated | PUB |
| TEST-101 | Docs | With the customer's 24-hour window open, a document is sent as a normal reply with no template; the path used is logged | integration | PUB |
| TEST-102 | Docs | With the window closed and consent recorded, the approved utility template is used; without consent only the manual link is offered | integration | PUB |
| TEST-103 | Identity | A WhatsApp number is linked to a reseller only after their first inbound message and staff confirmation | integration | O |
| TEST-104 | AI | Price, stock, order-status and opening-hours questions are answered without any model call; open questions reach the model | integration | A |
| TEST-105 | AI | A hard case escalates from the small model to the larger one; the cached prompt is reused | integration | A |
| TEST-106 | Ops | Stopping a service raises an Uptime Kuma alert to the owner in Telegram; an error appears in GlitchTip | manual | PUB |
| TEST-107 | Ops | A backup to R2 or B2 restores on a clean machine | manual | PUB |
| TEST-108 | Brand | The tokens contrast test fails if any text pair is below WCAG AA 4.5:1 (light and dark); gold on the light page is decorative only and rejected as text | unit | E |
| TEST-109 | Brand | Original logo, transparent/gold/white versions, favicon and Telegram avatar sizes exist; receipt (80 mm) and invoice (A4) headers render in Arabic (RTL) and English | manual | E |
| TEST-110 | Brand | Diva Ops and Control Room use only tokens (no hard-coded colors) and render in light/dark, RTL/LTR | integration | E |
| TEST-111 | Brand | The POS Next CSS-variable override patch rebases on the pinned version and the counter matches the palette | manual | E |
| TEST-112 | Brand | The ERPNext logo and app name are set by the config (0 changes on re-run); labels and receipts match the brand | manual | E |
| TEST-43 | Security | Webhook signatures verified; replayed webhook ignored | integration | all |
| TEST-44 | Counter | A browser-supplied price or discount that differs from the price list or role limit is rejected by the server | integration | E |
| TEST-45 | Counter | A counter invoice's payment appears in the ledger and the receivables report shows zero outstanding | integration | E |
| TEST-46 | Counter | Resuming a held draft and submitting it updates that draft; no second invoice or ghost draft remains | integration | E |
| TEST-47 | Counter | Submitting the same sale twice (retry or double click) creates one invoice | integration | E |
| TEST-48 | Counter | A user without the right role cannot post a payment entry or create items or prices | integration | E |
| TEST-49 | ERP | Purchase Invoice with Update Stock raises stock once and creates a supplier payable | integration | E |
| TEST-50 | ERP | A payment through a Bank-type mode (InstaPay, Bank Transfer) succeeds with reference number and date | integration | E |
| TEST-51 | Migration | After retirement, legacy invoices, payments, items and barcodes remain intact and printable | manual | E |
| TEST-52 | Migration | Barcodes generated by the legacy app still scan to the same items in POSNext and Ops | manual | E |

## 2. Performance targets (measure on the real machines)
UI actions under 100 ms; product search and barcode resolution under 500 ms on the store LAN; invoices of hundreds of lines remain usable; gateway call p95 under 1.5 s over the Link; catalog change visible in the cloud within 60 s. Record measurements; do not claim targets without them.

## 3. Security checklist
- Rotate exposed secrets (P0-01); secret scanning in CI.
- ERPNext reachable only from `local-api`; the Link is the only path between nodes.
- Every endpoint authenticated; service tokens for node-to-node; sessions with CSRF protection for browsers.
- MFA for owner and `payment_reviewer`.
- Role checks on the server; least privilege in ERPNext.
- Verify signatures for Chatwoot, Bosta and Telegram webhooks; deduplicate by event ID.
- Per-user ERPNext credentials encrypted at rest; fallback integration user with actor stamping.
- Private object storage, signed expiring URLs, content-type validation, size limits, EXIF stripping, rate limits.
- Personal data removed before RAG; retention jobs enforced; consent records for marketing.
- Mask phone numbers for roles that don't need them.
- Egypt Personal Data Protection Law: collect only what is needed, state retention, honor deletion requests.
- Audit log for all sensitive actions; export and pause actions logged.
- Dependencies pinned; script URLs pinned to exact versions.

## 4. Observability
Structured logs with request IDs; GlitchTip (Sentry-compatible, self-hosted) for errors and Uptime Kuma for uptime; health endpoints; alerts to the owner in Telegram for link state, failed jobs, dead letters, cash variance, large discounts, overrides, webhook failures, budget thresholds (messaging and AI spend); weekly summary of failures.
