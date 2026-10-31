# 07 Front-End Applications

All front ends are React + TypeScript PWAs sharing `packages/ui`, `auth`, `i18n` and `api-client`. Arabic RTL first with a full English alternative (DEC-11, DEC-39; specification in `19`), light and dark themes, touch targets at least 44 px, plain-language errors.

**Rollout note (DEC-03):** in Phase E, staff first work in the simplified ERPNext Desk configured per `05a-erp-configuration.md` (purchasing, suppliers, expenses, reports, back-office invoices). The Ops screens below are built in slices where Desk is too slow or lacks a needed control (scanning, labels, POS, packing). Do not rebuild a Desk screen that works.

## Role matrix
| Action | owner | manager | cashier | warehouse | accounts | payment_reviewer | sales |
|---|---|---|---|---|---|---|---|
| Counter sale | ✔ | ✔ | ✔ | | | | |
| Discount above 5% | PIN | PIN | | | | | |
| Receive, transfer, count | ✔ | ✔ | | ✔ | | | |
| Submit Payment Entry | ✔ | | | | ✔ | | |
| Verify payment proof | ✔ | | | | | ✔ | |
| Approve resellers, tiers | ✔ | ✔ | | | | | |
| Create shipment | ✔ | ✔ | | ✔ | | | ✔ |
| Settings, pause AI | ✔ | | | | | | |
| Reports, audit log | ✔ | ✔ | | | | | |

## M-OPS (`apps/ops-pwa`, served by local-api)
Task-based screens; home depends on role. Never calls ERPNext directly.
| Screen | Function | ERPNext document |
|---|---|---|
| Items | Barcodes, pack barcode (UOM), product rules, shade variants, duplicate check | Item, Item Barcode |
| Labels | Pick items and copies, preview, print EAN-13 labels (dozen and piece) drawn by the app (no ERPNext print format) | none |
| Receive | Supplier purchase (local): scan or pick items, supplier invoice number and date, rates per dozen, receiving warehouse, extra charges, ordered versus received quantity and discrepancies, payment method, amount and reference linked to the invoice; batch and expiry for cosmetics | **Purchase Invoice with Update Stock** (Stock Entry only for opening and non-purchase stock) |
| Invoices | Sales Invoices, Purchase Invoices, payment receipts, statements: Print, Download PDF, Open in WhatsApp, Send via WhatsApp, send status (`22`) | Sales Invoice, Purchase Invoice, Payment Entry |
| Import purchase | China orders: purchase order, partial receipts and discrepancies, landed costs (freight, insurance, customs), foreign currency, advances, bank-only payments | Purchase Order, Purchase Receipt, Landed Cost Voucher, Purchase Invoice, Payment Entry (simplified Desk first; an Ops screen only if Desk proves too slow) |
| Transfer | From and to warehouse, two-step via In Transit | Stock Entry (Material Transfer) |
| Count | Barcode cycle counts and opening stock | Stock Reconciliation |
| Invoice (back office) | Manager-created invoices with payment terms or installments for approved resellers | Sales Invoice, Payment Terms |
| Collect | Due today, overdue, customer statement, allocate a payment | Payment Entry, Receivable report |
| Payments to post | Draft Payment Entries from verified proofs | Payment Entry |
| Pack | Scan lines of the Delivery Note at ready-for-dispatch; the Sales Invoice is then created with the deposit advance allocated | Delivery Note, Sales Invoice |
**UX rules:** the scan field is always focused; camera scanning on phones; sound or vibration per scan; repeat scan raises quantity; unknown or wrong item shows a large red message and adds nothing; stale-response guard so a late async response never overwrites a later choice; every stock or payment action shows a summary first and offers undo or cancel; scans continue through brief connection drops and sync later, but stock and payment postings need a live connection.

## M-Desk (owner Desk workflows: `diva_desk` + `diva_guard`, DEC-85)
**Decision:** the owner's own Desk screens are ERPNext documents plus one thin keyboard/UX layer, not new screens. `diva_desk` is a client-only app (no doctypes, loaded with `app_include_js`) that focuses the right field, moves Tab in the order the owner types, accepts the first Link suggestion, opens the **Add New Item** dialog and draws the 50×30 mm EAN-13 label, and offers **Pay** (full or partial, Cash by default) and **Print** on a submitted Sales Invoice. Every permission, amount and stock decision runs on the server in `diva_guard.desk_api` (DEC-85, DEC-87). A Purchase Receipt submit creates its Purchase Invoice (ERPNext mapping, `update_stock = 0`) and moves the received stock to **Stores - DD** (DEC-86); Opening Stock is no longer part of Item quick entry (DEC-88). The Desk search bar (Ctrl+K) is extended through the `awesomebar_search` hook for item barcode, party phone and invoice id. Report printing uses Diva formats named after each report (DEC-89). A staff **Product Info** page at `/product_info` resolves a scanned barcode or a typed code/name to one card — code, name, group, EAN-13 image, product image, Dozen/Nos price, total stock and the warehouses holding it (DEC-95); it is a stopgap for the planned Diva Ops Items screen.

## M-POS (counter: POSNext + `diva_guard`, DEC-29)
**Decision (DEC-29, DEC-34):** the counter uses **POS Next by BrainWise** (`pos_next`; open source, AGPL-3.0, Vue 3, offline-capable, ERPNext 15 and later; see `14` for the name warning, risks and feature decisions) configured through POS Profile, plus the minimal `diva_guard` app and a small POSNext patch set. Plan: (1) configure POSNext with no code; (2) put every business rule in `diva_guard` server hooks so the UI cannot bypass them; (3) patch POSNext only for UI gaps (MOQ message, manager-PIN dialog, dozen display, Arabic labels), kept as a rebasable patch set and offered upstream where possible. AGPL: keep the fork's source available to its users. `TASK-P0-03` is a fit test to confirm v16 compatibility, offline behavior, reservation awareness and the hook points; if it fails, fall back to building a POS mode in Diva Ops.

**POS-CHECK (acceptance for either path):**
1. Barcode scan with multiple barcodes and UOM; repeated scans raise quantity.
2. MOQ and step enforced at the counter (RULE-MOQ).
3. Customer switching; the default customer never overwrites a deliberate choice.
4. Customer-specific price lists; last price sold shown.
5. Discount up to 5% for cashier; above needs manager PIN, audited.
6. Full payment only: cash or non-cash modes (DEC-14).
7. Hold and resume through POSNext drafts; resuming updates the same draft; held sales are never identified by `docstatus = 0` alone.
8. Thermal receipt (80 mm) and A4; printing never resubmits; auto-print is a setting.
9. Shift open and close with per-mode reconciliation and variance flag.
10. Returns and exchanges with credit note and Returns warehouse.
11. Cosmetics: batch selection FEFO, expired blocked.
12. Cannot consume stock reserved for chat orders (RULE-STOCK).
13. Keyboard-only operation on the real keyboard with the owner's current key map (F1 help, F2 customer, F3 quantity, F4 discount, F5 note, F6 delete line, F7 held sales, F8 payment, F9 print, F10 new sale, Ctrl+F search, Ctrl+Delete clear, Ctrl+Z undo, Ctrl+R return), run in a standalone window with `preventDefault`; configurable; a fallback key for any key a browser or OS blocks.
14. Arabic RTL and English switch.
15. Works with no internet while the store LAN is up.
16. No ERPNext core modification and no custom code inside ERPNext.
17. Performance: UI actions under 100 ms, search and barcode under 500 ms, invoices of hundreds of lines usable.
18. **Scan info card:** every scan shows item name, item code, price per dozen and stock, and the quantity added, then returns focus to the barcode field.
19. `qty*barcode` multiplier scan adds that quantity in one scan.
**Safety rules:** never show success before the server confirms; after an uncertain submit read the server state before retry; lock actions on click and use an idempotency key per sale; submitted invoices are never edited in place; unsaved work survives refresh.

## M-CONTROL-ROOM (`apps/control-room`, cloud)
Pages by phase: Overview (needs-attention queue first); Orders (filters by status, date, reseller, city, product; order detail with rule results, proofs, ERPNext and Bosta links, timeline; staff order entry; shipping quote); Payment proofs; Resellers; Inbox context panel; Content queue; Broadcast (one-click send with cost preview, free channels first; `22`); Shipments; Settings; Audit log; AI monitoring (handoff rate, guardrail blocks, kill switch); Media review; Market; System health (link state, queues, failed jobs with safe retry); Sales and stock (today's gross, returns, net, by mode, by cashier, top products, low stock, expiry, receivables, exceptions). Server-side aggregation only. Live updates through server-sent events.
**AC:** a verified proof appears in Ops under Payments to post; the link banner appears within one minute of an outage.

## M-TELEGRAM-ADMIN (`apps/cloud-api`)
Role-based commands: `/orders` with filters (`status=`, `date=`, `reseller=`, `city=`, `product=`, `min=`), `/order <id>`, `/proofs`, `/resellers`, `/ship <id>`, `/neworder`, `/due`, `/stock`, `/brief`, `/pause`, `/resume`, `/post` (Phase PUB), `/prices` (Phase G). Inline buttons. Owner alerts: link state, large discounts, overrides, cash variance, deleted lines, failed jobs. One process owns incoming Telegram updates (webhook mode).

## M-MINI-APP (`apps/mini-app`, Phase M)
Verify `initData` server-side. Approved resellers only for prices. Catalog, search, SKU quick-add, MOQ-aware cart with progress to the 3,000 EGP minimum, basket-gap suggestions, checkout with address picker, reorder, tracking, support button into Chatwoot. Prices always revalidated on the server.
