# 09 Build Plan

Order (DEC-03): **P0 → E → PUB → O → B → C → A → M → G**. There are no fixed dates (DEC-23). Each phase ends at an exit gate; the next phase starts only when the gate passes. Effort is an estimate for one developer working with an AI coding agent, in hours.

| Phase | Name | Effort (h) |
|---|---|---|
| P0 | Foundations and decisions | 35–55 |
| E | ERPNext: simplify, operate, POS | 370–620 |
| PUB | Publishing to Facebook, WhatsApp, Telegram, Instagram, TikTok | 180–300 |
| O | Chat orders engine | 150–230 |
| B | Bosta shipping and reports | 70–110 |
| C | Chat hub, human-first | 60–100 |
| A | AI agent with voice and images | 200–300 |
| M | Telegram Mini App | 110–160 |
| G | Growth | later |
| | **Total P0 to M** | **about 1,175–1,875** |

Task rule: every task has acceptance criteria (AC) and dependencies (Dep). A task is done only when AGENTS.md's Definition of Done is met.

## Phase P0 — Foundations and decisions
| ID | Task | Dep | AC |
|---|---|---|---|
| P0-01 | Rotate every exposed credential (Telegram bot token, Meta tokens, URL-shortener token, webhook verify token); move to secret stores | none | Old credentials revoked; secret scan clean; nothing in workflow JSON |
| P0-02 | Disable or authenticate the legacy "Nanobot" webhooks | none | Unauthenticated calls return 401 or endpoints are gone |
| P0-03 | **POS Next fit test (2–3 days):** install BrainWise `pos_next` (not the exvas "POSNext") on staging with a copy of production data; run POS-CHECK in `07`; answer every "verify" and "unknown" cell in `14` including Arabic completeness, RTL, Arabic keyboard layout and Arabic receipt printing (ERPNext 16 compatibility, full-shift offline test, reserved-stock behavior, hook points for `diva_guard`, receipt printing and QZ Tray, Arabic RTL, `qty*barcode` multiplier, UOM Dozen and Nos handling, returns, customer card, uninstall rehearsal) | P0-04 | Scored written result and a go or no-go DEC; if no-go, build a POS mode in Diva Ops |
| P0-04a | **Install a disposable dev ERPNext 16** with `scripts/start-dev-erpnext.sh` (frappe_docker `pwd.yml`; pin the image tag to version 16 if it is not already) and record the versions | P0-10 | ERPNext answers on port 8080; versions recorded in `docs/appendix-erpnext-verification.md` |
| P0-04 | Verify ERPNext on staging: version, installed apps, stock reservation behavior, Item Barcode with UOM, Dozen whole-number UOM, Payment Terms, credit limit, the REST endpoints the adapter needs | P0-04a | Findings file in `docs/appendix-erpnext-verification.md` |
| P0-05 | Measure infrastructure: store VM capacity, internet uptime and latency to the chosen cloud region, WireGuard feasibility, UPS | none | Numbers recorded; cloud provider chosen |
| P0-06 | Hardware inventory and test: scanner, thermal receipt printer, label printer; browser print and QZ Tray with Arabic text | none | Models recorded; Arabic receipt and label print correctly |
| P0-07 | WhatsApp: identify current API provider, approved templates, number status; Chatwoot compatibility check; Meta business verification status; Instagram and Facebook Page connection status | none | Report with migration plan for later phase C |
| P0-08 | Accountant check: VAT, e-invoicing obligations, payment-mode account mapping | none | Written answer; OPEN-08, OPEN-10 closed or scheduled |
| P0-09 | Datasets: item master export, 100 anonymized chats, 50 voice notes; ERPNext backup and restore test | none | Datasets stored privately; restore proven on a separate VM |
| P0-10 | Monorepo, CI, Docker Compose (cloud and store), secret scanning, `make` commands | none | `make setup test lint` pass in CI |
| P0-12 | **Only if the legacy site still exists:** verify legacy-app findings on a staging copy (`13`); otherwise skip, because the legacy app is retired anyway: payment recording in Diva Sale invoices, held drafts, bank-type Payment Entry references, API duplicates | none | Results recorded in `13`; severity confirmed |
| P0-11 | Start the TikTok developer app and audit application; check Meta app permissions for Facebook and Instagram publishing | none | Applications submitted; status tracked |
**Exit gate P0:** no exposed secrets; P0-03, P0-04 results recorded; CI green; applications submitted.

## Phase E — ERPNext (first priority)
Spec: `05a-erp-configuration.md`, `07` (Ops and POS), `04` rules.
| ID | Task | Dep | AC |
|---|---|---|---|
| E-00a | **Install ERPNext 16 on the store VM (production)** with the frappe_docker production setup; HTTPS on the LAN; daily backups with an off-site copy; restore test; load items and customers by import, no demo data | P0-04 | ERPNext 16 runs on the store VM; restore test passed |
| E-00 | Legacy `diva_store` retirement plan and salvage (`13`) | P0-12 | Written plan, salvage list, rollback path agreed |
| E-01 | Baseline snapshot of site config; installed-apps inventory; **field register from the live site** | P0-04 | `erp-field-register.csv` complete, every row classified, no invented fieldnames |
| E-02 | Hide unneeded modules and workspaces per role | E-01 | Employee accounts cannot see hidden modules; no broken menus; tests pass |
| E-03 | `infra/erpnext-config/apply.py`: idempotent configuration script with diff report | E-01 | Re-running changes nothing; runs on staging first; reapplied after a simulated upgrade |
| E-04 | Units, items, groups, codes, valuation, negative stock off, cosmetics batch and expiry, simplified Item form | E-03, OPEN-13 | RULE-UOM tests pass: dozen purchase and sale, piece return |
| E-05 | Price lists per dozen, tiers, price-edit permissions | E-04 | Price fetch correct per customer; employee cannot edit price lists |
| E-06 | Barcodes: load dozen and piece barcodes, uniqueness, supplier EAN as extra | E-04 | Duplicate barcode rejected; dozen scan adds 1 dozen |
| E-07 | Warehouses (Main Inventory, Shop, Gallery, Returns and Defects, In Transit); opening stock count and import; FIFO audit on staging (RULE-COST) | E-04 | Stock reconciliation matches the physical count |
| E-08 | Purchasing: suppliers, **Purchase Invoice with Update Stock** (DEC-31), supplier payments, payables | E-04 | Purchase test passes with one stock movement per delivery |
| E-08b | **China import flow (DEC-75 EGP simplification):** Purchase Order, partial Purchase Receipts, Landed Cost Voucher, **EGP prices / no foreign currency or advances**, bank payments; **Quick local purchase** details (discrepancies, extra charges, payment at purchase) | E-08 | TEST-79 passes: 10 dozen paid 40% then 60% shows correct stock, value, supplier balance and payment history |
| E-09 | Sales, customers, payment modes (six) and account mapping, receivables | E-04, OPEN-10 | Sales, full payment, outstanding invoice and receivable report agree |
| E-10 | Expenses and cash tracking; daily cash closing checklist | E-09 | Cash report reconciles with ledger |
| E-11 | Taxes: confirm none (no VAT, no e-invoice); hide tax fields | E-01 | Invoices show no tax lines |
| E-12 | `local-api` skeleton, `erpnext-adapter` with contract tests, `rules-engine` counter rules (MOQ in dozens, discount limits, override audit) | E-04 | Contract tests pass nightly on staging; rules coverage 100% on branches |
| E-13 | Ops slice 1: Items and barcodes (port the EAN-13 generator), Labels (dozen and piece), Receive (Purchase Invoice), Transfer, Count, Collect | E-06, E-12 | TEST list for Ops passes; label scans back correctly |
| E-14 | **POSNext adoption:** install and configure (POS Profile, shifts, offline, QZ Tray receipts, Arabic), payment modes, cashier roles | E-12, P0-03 | POS-CHECK items 1, 3, 6–11, 13–15 pass |
| E-14a | `diva_guard`: server hooks for MOQ in dozens, discount limits by role with manager PIN, price integrity against the price list, no credit or partial payment at the counter, reserved-stock check; `Diva Product Rule` doctype; imports `rules-engine` | E-12, E-14 | TEST-02 to TEST-06 and TEST-44 to TEST-48 pass; the browser cannot bypass any rule |
| E-14b | POS Next patch set. **Required:** scan info card (name, code, price per dozen, stock), the owner's key map, MOQ message, PIN dialog, dozen display, Arabic labels, invoice-sharing buttons (Print, Download PDF, Open in WhatsApp). **If missing:** `qty*barcode` multiplier, undo last scan, low-stock tint. Rebased on upstream | E-14a | TEST-55 to TEST-57 pass; patches in git with tests; upgrade rehearsal on staging passes |
| E-14c | Cosmetics batch and expiry at the counter (FEFO) | E-14 | TEST-10 passes |
| E-14d | Pilot, cutover and legacy retirement (`13` section 4) | E-14b, E-00 | Legacy app uninstalled after backup; one week without a blocking issue |
| E-15 | Standard reports with saved filters; invoice A4, 80 mm receipt, payment receipt, statements | E-09 | Reports agree with ledger; Arabic prints correctly |
| E-16 | Roles and users: one ERPNext user per staff member; permission matrix; tests with employee accounts | E-02 | Matrix tests pass |
| E-18 | **Invoice sharing, level 1 (free):** Ops Invoices screen and POS Next buttons: Print, Download PDF, Open in WhatsApp (`wa.me` link with the normalized number and a ready Arabic or English message) for Sales Invoices, Purchase Invoices, payment receipts and statements; receipts and invoices also carry a "Message us" QR and link (`22`, ENH-C-09) | E-15, E-13 | TEST-92 passes |
| E-17 | Backups, restore test, downtime runbook, Arabic SOPs, staff training; retire daily Desk clutter | E-14d, E-15, E-16 | Staff complete the full workflow from SOPs; restore test passed |
| BRAND-01 | **Create `packages/ui` with `tokens.css` and `tokens.json` (light and dark) and a unit test that fails if any text pair drops below WCAG AA** (`27`, DEC-92) | P0-10 | `packages/ui/tokens.css` and `tokens.json` exist with the same tokens; the contrast test fails below 4.5:1 and passes with the documented ratios (light text on page 14.6, text on panel 15.8, secondary 6.5, white on navy 11.5, navy on gold 6.6, gold on navy 4.8, success 4.8, warning 4.7, error 6.5; dark text 15.0, secondary 8.4, gold 8.6, success 9.4, warning 9.1, error 8.0); gold on the light page is decorative only (2.2) |
| BRAND-02 | **Brand assets:** commit the original logo (`assets/brand/logo-original.jpg`), request the owner's transparent SVG/PNG and gold-on-navy and white versions (OPEN-22), bundle the IBM Plex Sans Arabic and thin-serif font files, create favicon and Telegram channel avatar sizes, and build the receipt (80 mm) and invoice/print header (A4) layouts from the tokens in Arabic and English | none | Original logo committed; transparent/gold/white versions received or explicitly tracked in OPEN-22; font files bundled and complete Arabic glyphs checked; favicon and avatar files exist; receipt and A4 headers render in Arabic (RTL) and English using only tokens |
| BRAND-03 | **Apply the tokens to the Diva Ops and Control Room shells** when they exist: light and dark mode, RTL and LTR, no hard-coded colors | E-13 | Both shells load `tokens.css`; a search finds no hard-coded hex colors in their styles; light/dark and Arabic/English render correctly; the contrast test stays green |
| BRAND-04 | **POS Next theming through CSS-variable overrides** in the existing patch set (`infra/posnext-patches`); keep it small and rebasable | E-14 | One small tracked patch (or a short patch series) overrides the POS palette with the Diva tokens; it rebases cleanly on the pinned POS Next version; a visual check of the counter passes |
| BRAND-05 | **Set the logo and app name in ERPNext through Navbar and Website settings** via `infra/erpnext-config` (configuration data only), with a visual check on labels and receipts | E-03 | Re-running the config reports 0 changes; the Desk and website show the Diva logo and name; labels and receipts match the brand; no Desk theme app and no core edit |
**Exit gate E:** acceptance list in `05a` section 14 passes; POS-CHECK passes; staff use the new system for daily work for one full week without a blocking issue.

**Delivered ahead of the plan (owner requests, 2026-10-29):** **ENH-E-01** Party Statement report and print format (`custom_reports`); **ENH-E-02** Desk workspaces, number cards and store analytics (`desk.yaml` + `apply_desk.py`); **ENH-E-03** POS Next Escape-to-close for custom popups (patch 0013); **ENH-E-04** EOD print format fix (patch 0014); **ENH-E-05** Desk workflows (`diva_desk` + `diva_guard.desk_api`, DEC-85 to DEC-89). These do not replace the planned E-17 (backups/training) or E-18 (invoice sharing).

## Phase PUB — Publishing (second priority)
| ID | Task | Dep | AC |
|---|---|---|---|
| PUB-01 | Cloud foundation: `cloud-api`, Postgres, auth with MFA, audit log, object storage, observability, deploy to a small VPS first (2 vCPU, 4 GB; resize when chat and AI start), media and backups on Cloudflare R2 or Backblaze B2, self-hosted Uptime Kuma and GlitchTip | E exit | Health and alerts working; MFA enforced for owner |
| PUB-02 | WireGuard Link, gateway endpoints for health and catalog changes, catalog sync to the cloud cache | PUB-01, E-12 | Item change appears in the cloud cache within 60 seconds; zero drift on reconcile |
| PUB-03 | Telegram admin bot skeleton with roles; owner alerts | PUB-01 | Role checks enforced; alert delivered |
| PUB-04 | Control Room shell: login, roles, content queue, system health | PUB-01 | Pages load from the cloud API |
| PUB-05 | Publish gate: product needs barcode, price, MOQ, pack size, images, stock fields | PUB-02 | Missing-field product cannot be approved |
| PUB-06 | AI caption and image enhancement with preview (Approve, Regenerate, Edit); real photo stays the base | PUB-04 | Nothing publishes without approval; prompts and source photo stored |
| PUB-07 | Facebook Page publishing, pinned Graph API version, retries, post IDs | PUB-06, P0-11 | Post appears; failure retries then alerts |
| PUB-08 | Instagram publishing | PUB-06 | Same as PUB-07 |
| PUB-09 | Telegram channel publishing | PUB-06 | Same |
| PUB-10 | **WhatsApp both ways:** (a) broadcast templates to opted-in contacts with consent records, segments, cost preview, optional budget cap (off by default, DEC-33), rate limits; (b) ready-to-post pack for Channel or Status | PUB-06, P0-07 | Template approved by Meta; no send without consent; optional budget cap works when enabled; pack delivered to staff |
| PUB-11 | TikTok: upload or draft mode now; direct posting after audit | PUB-06, P0-11 | Draft appears; direct post only after audit approval |
| PUB-12 | Publishing report and public-price check | PUB-07 | No public post contains a wholesale price; failure list visible |
| PUB-13 | **Invoice sharing, level 2 (one click):** Send via WhatsApp by the cheapest valid path (free reply inside an open 24-hour window, else approved utility template with document header, else the manual link), local outbox, idempotency, delivery status (`22`) | PUB-02, E-18, P0-07 | TEST-93 to TEST-96 pass; 1,000 sends cost about $3.60 |
| PUB-14 | **One-click broadcast** page: audience, cost preview, confirmation, free channels first, consent and STOP handling (`22`) | PUB-10, PUB-13 | TEST-97 to TEST-100 pass |
**Exit gate PUB:** one approval publishes to Facebook, Instagram and Telegram; WhatsApp broadcast and pack both work; TikTok works to the level the audit allows.

## Phase O — Chat orders engine
| ID | Task | Dep | AC |
|---|---|---|---|
| O-01 | `rules-engine` chat rules: 3,000 EGP minimum, basket-gap suggestions, shipping step, availability | E-12 | TEST rules cases pass |
| O-02 | Cart and draft API; staff order entry (SKU or barcode) in Control Room and Telegram `/neworder` | O-01 | Staff enter a chat order with live rule errors |
| O-03 | Order, payment and shipment state machines with transition guard and audit | O-01 | Matrix tests in `05` pass |
| O-04 | Gateway order create-or-get; reserve only after the required payment is verified; release; deposit-deadline expiry job | O-03, PUB-02 | Duplicate create returns the same order; timeout then retry yields one Sales Order; expiry releases stock |
| O-05 | Shipping quote step (staff sets fee) | O-03 | AI path cannot quote shipping |
| O-06 | Payment proofs, append-only ledger, human verification, draft Payment Entry as customer advance, Payments to post, deposit calculation (30% for new resellers) | O-03 | No automated path verifies payment; repeat verification creates one ledger entry |
| O-07 | Notifications: outbox, templates, 24-hour window, dead-letter queue | O-03 | Dead letters visible; retries with backoff |
| O-08 | Settings with versions and effective dates; replicate to local | PUB-04 | Order keeps its `rule_set_version` |
| O-09 | Link-down circuit breaker and customer notice | PUB-02 | New orders blocked within about 45 s; notice sent; resumes after 3 successes |
| O-10 | Ready-for-dispatch step: Delivery Note then Sales Invoice, allocate deposit advance, reconcile balance | O-04, O-06 | Invoice equals goods plus shipping; advance allocated; remaining balance correct (TEST-85, TEST-86) |
**Exit gate O:** TEST cases O in `10` pass.

## Phase B — Bosta
B-01 client and staging environment, manual courier support (courier, tracking number, fee, status, outcome; preferred courier on the reseller profile); B-02 address normalizer to city, zone, district IDs with confirmation; B-03 shipment creation with preconditions and scan-to-pack warning; B-04 webhook receiver (verify, deduplicate, map states, notify); B-05 returns and exchanges; B-06 COD remittance reconciliation; B-07 manager reports (counter and chat). **AC:** duplicate webhooks send one notification; no shipment without resolved address IDs and met payment preconditions. **Exit gate B:** order traced from draft to delivered in staging.

## Phase C — Chat hub, human-first
C-01 deploy Chatwoot; connect WhatsApp (migrate from the current provider with no message loss), Instagram, Facebook; C-02 durable inbound events and dedup; C-03 ownership and takeover rules with version check; C-04 template management; C-05 inbox context panel in Control Room. **Exit gate C:** staff run all three channels from one inbox for a week; no lost messages.

## Phase A — AI agent
A-01 orchestrator and tools; A-02 guardrails; A-03 evaluation set and replay; A-04 shadow mode; A-05 staff-assisted drafts; A-06 limited auto-replies for low-risk intents; A-07 media (voice, images, proofs) per `08`; A-08 RAG with anonymized chats; A-09 expansion and kill switches; A-10 router for routine intents (price, stock, order status, opening hours) answered by fixed logic and templates before any model is called; A-11 small-model-first with escalation to a bigger model for hard cases, plus prompt caching. **Gates:** each stage passes the evaluation thresholds (rule correctness, handoff correctness, zero invented facts, zero guardrail breaches) before the next begins.

## Phase M — Mini App
M-01 `initData` verification; M-02 catalog and search; M-03 MOQ-aware cart with minimum progress; M-04 checkout, tracking, reorder. **Exit gate M:** a reseller completes an order with no staff retyping.

## Phase G — Growth (later)
Market price monitor, restock and new-arrival campaigns, reseller tiers and credit controls, TikTok DM via partner, analytics, margin and reorder reports, supplier purchasing automation.


## Accepted enhancements (DEC-37)
Accepted items from `16` join these phases. Each is a task with its own acceptance criteria written in `16` and checked at the gate. Effort is in addition to the table above.

| Phase | Accepted enhancements | Effort (h) |
|---|---|---|
| P0 | ENH-R-01, ENH-R-03, ENH-R-04, ENH-S-01, ENH-S-02 | about 30 |
| E | ENH-A-01, ENH-A-02, ENH-A-03, ENH-A-04, ENH-A-05, ENH-A-06, ENH-A-07, ENH-A-10, ENH-C-01, ENH-C-02, ENH-C-03, ENH-C-04, ENH-I-01, ENH-I-05, ENH-I-07, ENH-R-05, ENH-R-06, ENH-R-07, ENH-S-03, ENH-S-09 | about 176 |
| PUB | ENH-M-01, ENH-M-02, ENH-M-03, ENH-M-04, ENH-M-05, ENH-M-06, ENH-M-07, ENH-L-01, ENH-L-02, ENH-L-03, ENH-I-02, ENH-I-04, ENH-K-01, ENH-K-02, ENH-S-04, ENH-S-05, ENH-S-08 | about 186 |
| O | ENH-C-06, ENH-M-08, ENH-S-06 | about 60 |
| C | ENH-H-01, ENH-H-04, ENH-H-05 | about 46 |
| A | ENH-H-02, ENH-H-03, ENH-H-08, ENH-H-10 | about 38 |
| All gates | ENH-R-02 | about 20 |

**With the accepted enhancements the total for P0 to M is about 1,620–2,570 hours** (base 1,175–1,875 plus about 556 h at 80%–125%).

Gate additions: P0 gate also requires ENH-R-01, R-03, R-04, S-01, S-02. Gate E also requires the cutover plan and opening balances signed (ENH-R-05, A-01) and the recovery drill (ENH-S-03). Every gate uses the scripts in `18`.

## Localization tasks (DEC-39)
Tasks `I18N-01` to `I18N-11` in `19` join these phases: P0 (glossary, fonts, printer test), E (ERPNext Arabic, print formats, POS Arabic, search, product names, SOPs), PUB (shared locale package, bilingual publishing and templates), A (customer language handling). Effort about 90 h (70–120 h). **Total for P0 to M including accepted enhancements, localization and the v4.1 additions: about 1,870–3,030 hours.** The v4.1 additions (China imports, deposits and advances, effective-discount and price-conflict rules, stricter returns, manual couriers) are about 90–170 hours. The v5.0 additions (WhatsApp invoice sending and one-click broadcast) are about 50–90 hours.

## Dependencies summary
P0 → E → PUB → O → B → C → A → M. Exceptions: P0-11 runs in parallel with E so audits finish early; the TikTok and Meta permission waits must not block E.
