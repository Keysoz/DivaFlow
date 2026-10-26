# Appendix: POS Next fit test (TASK-P0-03)

**Status: partial — hardware/visual checks pending; uninstall rehearsal done.** The owner deferred the scanner, thermal receipt printer and label printer to a later session (P0-06) and authorised synthetic data instead of a production-data copy (owner, 2026-10-26; recorded in DEC-68). Everything that can be verified without the hardware was verified on the disposable dev stack (section 1 of `appendix-erpnext-verification.md`) with synthetic data. No production data or credentials were used (DEC-38).

Date: 2026-10-26. Site: `frontend` (erpnext 16.52.1, frappe 16.53.0).

## 1. What was installed

| Item | Value |
|---|---|
| App | POS Next by BrainWise, repository `BrainWise-DEV/POSNext` (never the exvas "POSNext") |
| **Tested build** | `47d2c9a` (branch `develop`, 2026-10-25); app version reports `2.0.0` |
| Pinned release tag | `v2.0.0` = commit `e0a52c5` (2026-09-08); **the tag ships app version `1.17.0`** and is 182 commits behind the tested build — see the pinned re-run in section 1c |
| ERPNext 16 compatibility | Install and migrate succeeded on erpnext 16.52.1 / frappe 16.53.0 |
| Custom fields at `47d2c9a` (vendor-owned, DEC-29) | **37**: Customer 2 (`custom_district`, `custom_governorate`; module blank), Journal Entry 8 (POS expenses), Mode of Payment 1 (wallet), POS Closing Shift 1 (bank deposit), POS Profile 10 (9 `posa_*` expense/block settings + `custom_brands_table`), Pricing Rule 1 and Promotional Scheme 1 (`one_time_per_customer`, module `POSNext Promotions`), Sales Invoice 6, Sales Invoice Item 2 (`sales_person`, `customer`), Sales Order 2 (`pos_profile`, shift), Sales Person 3 (commissions). At **v2.0.0 this is 21** (verified in the pinned re-run, section 1c). |
| Other records added | Print Format `POS Next Receipt`; roles `POSNext Cashier`, `Nexus POS Manager` and their Custom DocPerms |
| Core modifications | None by this task. The app overrides the Sales Invoice class (`override_doctype_class` → `CustomSalesInvoice`) and monkeypatches a few ERPNext classes at import (rounding, packed items) — vendor code, no core files edited |
| Frontend build | `yarn install` + `yarn build` with Node 24 (v24.15.0 binary downloaded into the container; the host has 24.19.0), Vite 6: succeeded; PWA service worker generated with 53 precache entries (~7 MB) |
| Dev-only workaround | The `pwd.yml` backend image has no Node, so `bench get-app` aborts after cloning; the app was registered in `sites/apps.txt`, installed, then pip-installed (`pip install -e`) and its built assets copied into the frontend container. Production packaging (Dockerfile with Node build stage) is part of E-14 |

Health after install: `GET /pos` → 200, built JS/CSS/manifest/service worker → 200.

### 1a. Hook points for `diva_guard`

- The app registers `doc_events` on **Sales Invoice**: `validate` (one-time offers + wallet), `before_submit` (its own authorization gate), `on_submit`, `before_cancel`, `on_cancel`, `after_insert`.
- It also replaces the Sales Invoice class (`override_doctype_class` → `pos_next.overrides.sales_invoice.CustomSalesInvoice`).
- `diva_guard` can register its own Sales Invoice `validate` / `before_submit` handlers: Frappe composes multiple doc-event handlers, so both run and the browser cannot bypass them (DEC-30). Do not rely on ordering between apps; validate independently.
- No conflict was observed: install, POS invoice submit and cancellation all worked with the vendor override in place.

### 1b. Uninstall rehearsal (DEC-35)

- `bench uninstall-app pos_next` removed the app's Module Defs and doctypes (`POS Barcode Rules`, `POS Opening Shift`, `POS Governorate`, `Sales Person Item Group Commission`, `POS Authorization Log`), the module-linked custom fields and the `POS Next Receipt` print format; `/pos` returned 404 afterwards.
- **Left behind:** 4 vendor custom fields (Customer `custom_district` / `custom_governorate`, Pricing Rule and Promotional Scheme `one_time_per_customer`), the two roles with their Custom DocPerms, and the built assets in the frontend container. The vendor uninstaller deletes only 2 fields explicitly (`Sales Invoice-posa_pos_opening_shift`, `Sales Invoice-posa_is_printed`) and relies on Frappe's module cleanup for the rest.
- Reinstall restored all 37 custom fields and `/pos` → 200; the site stayed healthy (ping pong). Consequence for E-14: plan a cleanup of the 4 orphans (or accept and document them); never assume uninstall is complete.

### 1c. Pinned `v2.0.0` smoke re-run (2026-10-27)

Pinned tag: **`v2.0.0` = commit `e0a52c5`** — but the tag ships app version **`1.17.0`** (`__version__ = "1.17.0"`), a vendor tag/version mismatch. It is materially older than the tested `develop` build.

| Check | Result at v2.0.0 |
|---|---|
| Install/migrate on ERPNext 16.52.1 | **PASS** |
| Custom fields | **21** (includes 2 on `Promotional Scheme Price Discount`); was 37 at develop |
| Arabic `/ RTL` | `ar.csv` 1,590 lines (vs 1,712); `useLocale` RTL present |
| Global F-key handlers | **none** (the F4/F8/F9 handlers exist only on `develop`) |
| `qty*barcode` | absent |
| Scan info card | absent |
| Repeated scan raises quantity | present (`mergeItems`) |
| Returns dialog | present (`ReturnInvoiceDialog.vue`) |
| POS invoice, 2 Dozen, cash | **PASS** — EGP 2,880, paid 2,880, change 0, `stock_qty` 24 |
| Reserved-stock block | **PASS** — blocked while fully reserved (`NegativeStockError`); after cancelling the reservation the same invoice submitted, stock 96 → 72, the other order's 24 stayed reserved |
| Offline / PWA | **LIMITATION** — the service worker is served at `/assets/pos_next/pos/sw.js`, so its scope cannot control `/pos`; `/pos-sw.js` is 404 at v2.0.0. The develop build adds a root-scope copy (`www/pos-sw.js`). Needs a patch or a newer release before offline is claimed. |
| Uninstall rehearsal | uninstall succeeds, `/pos` 404; **10 custom fields** and the two roles remain (the vendor removes only 2 explicitly; the rest depend on module cleanup). Reinstall restores 21 fields and `/pos` 200. |

**Verdict impact:** the pin condition is satisfied for tag pinning, but `v2.0.0` is code `1.17.0`: no global F-keys, fewer fields and an offline scope gap. The required patch set therefore grows (keymap, scan card, `qty*barcode`, service-worker scope). Re-run this smoke subset on the patched pinned build before E-14; the hardware session is still pending.

## 2. POS-CHECK results (docs/07 M-POS)

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Barcode scan, multiple barcodes and UOM; repeated scans raise quantity | **PASS (API + code)** — cart merges an existing line and raises the quantity (`mergeItems`); an item with Dozen and Nos barcodes works in ERPNext. Physical scanning is pending (hardware). | `posCart.js` merge logic; item `P004-DOZEN` barcodes `2000000000015` (Dozen) / `2000000000022` (Nos) |
| 2 | MOQ and step at the counter | **Pending by design** — arrives with `diva_guard` (E-14a, RULE-MOQ); the app has no MOQ rule | — |
| 3 | Customer switching; default customer never overwrites a choice | **Not exercised (browser)** — customer dialog exists (`customer dialog` in docs/14); to confirm during the hardware/UI session | code only |
| 4 | Customer-specific price lists; last price sold | **Partial** — POS Profile carries `selling_price_list` and the POS invoice used it; "last price sold" display not confirmed | POS invoice `ACC-SINV-2026-00001` |
| 5 | Discount up to 5%, manager PIN above, audited | **Pending by design** — `diva_guard` (E-14a) plus the POS Next PIN dialog patch (E-14b) | — |
| 6 | Full payment only (cash or non-cash) | **PASS (API)** — POS invoice with cash payment: `grand_total` 2,880, `paid_amount` 2,880, `change_amount` 0; credit/partial blocking is a setting + `diva_guard` rule | `ACC-SINV-2026-00001` |
| 7 | Hold and resume through drafts | **Not exercised (browser)** — `draftManager` and held-sales UI exist | code only |
| 8 | 80 mm receipt and A4; printing never resubmits | **Pending (hardware)** — `qz-tray` dependency and `useQzTray` composable are present; `POS Next Receipt` print format installed | code |
| 9 | Shift open and close with per-mode reconciliation | **Partial** — POS Opening Entry submitted (`POS-OPE-2026-00001`, cash 500); closing/reconciliation not exercised | API |
| 10 | Returns with credit note and Returns warehouse | **Present, not exercised** — `ReturnInvoiceDialog.vue`; standard ERPNext returns available as the documented fallback | code |
| 11 | Cosmetics batch/expiry, FEFO, expired blocked | **Out of scope here** — TASK-E-14c | — |
| 12 | Cannot consume stock reserved for chat orders (RULE-STOCK) | **PASS (API)** — a POS invoice for 2 Dozen was rejected while all stock was reserved (`NegativeStockError: As the full stock is reserved…`); after cancelling one reservation the same invoice submitted and stock moved 120 → 96 Nos, leaving the other order's 24 Nos reserved | `ACC-SINV-2026-00001`, `SAL-ORD-2026-00001/2` |
| 13 | Keyboard-only operation with the owner's key map | **FAIL → required patch** — at the tested develop build only F4 (focus search), F8 (customer search) and F9 (payment) exist; at the pinned `v2.0.0` there are none | `pages/POSSale.vue` |
| 14 | Arabic RTL and English switch | **PASS (static), visual pending** — `useLocale.js` sets `dir: rtl`; `LanguageSwitcher.vue`; `ar.csv` has 1,712 lines (1,711 entries) for about 1,400 double-quoted `__()` calls | code |
| 15 | Works with no internet while the LAN is up | **Architecture PASS, full-shift test pending** — PWA service worker + workbox precache + `workers/offline.worker.js` + IndexedDB (`dexie`) | build output |
| 16 | No ERPNext core modification, no custom code inside ERPNext | **PASS** — 37 vendor-owned custom fields (at the tested build), 1 print format, no core file edits | see section 1 |
| 17 | Performance (UI < 100 ms; search/barcode < 500 ms; large invoices) | **Pending (browser)** | — |
| 18 | Scan info card (name, code, price per dozen, stock, qty added, focus returns) | **FAIL → required patch (E-14b)** — no dedicated scan card; the cart line shows name, code, rate and quantity, stock appears in the item dialog | code |
| 19 | `qty*barcode` multiplier | **FAIL → required patch (E-14b)** — no `*` parsing in the barcode path | code |

Safety rules (never show success before server confirmation, idempotency, no in-place edits): reviewed in code; confirm during the hardware/UI session.

## 3. Answers to the "verify"/"unknown" cells in docs/14

| Cell | Answer |
|---|---|
| Barcode is added on scan; repeated scan raises quantity — "yes (verify)" | **Yes** (merge logic); physical scan pending |
| `qty*barcode` multiplier — "unknown" | **No** → required patch E-14b |
| Undo last scan (Ctrl+Z) — "unknown" | **No** → optional patch candidate |
| Scan info card — "unknown" | **No dedicated card** → required patch E-14b |
| Returns — "verify" | **Yes** (ReturnInvoiceDialog); standard returns remain the fallback |
| Low-stock tint — "unknown" | **No evidence** → optional patch candidate |
| Keyboard shortcuts — "map unverified" | **Partial: F4/F8/F9 only** → required patch (full owner key map) |
| Offline — "yes (tested)" | Architecture present; full-shift test pending |

## 4. Verdict (provisional)

**Provisional GO for POS Next on ERPNext 16**, subject to these conditions before E-14 starts:

1. **Pin done: `v2.0.0` re-run executed (section 1c).** `v2.0.0` is code `1.17.0` (vendor tag/version mismatch) with 21 fields, no global F-keys and an offline service-worker scope gap. Before E-14, re-run the smoke subset on the **patched** pinned build; never auto-upgrade (DEC-35).
2. **Patch set E-14b is required**, not optional: `qty*barcode` multiplier, the owner's full key map with `preventDefault`, and the scan info card. Undo and low-stock tint remain optional. (At `v2.0.0` there are no global F-key handlers at all; the patch set grows.)
3. **Hardware session (owner):** Arabic receipt printing (80 mm), QZ Tray, Arabic keyboard layout, visual RTL and English switch, full-shift offline, performance figures, returns and shift closing end to end.
4. **`diva_guard` (E-14a) remains mandatory** for MOQ, discount/PIN, price integrity, full-payment-only and the reserved-stock check (RULE-STOCK).
5. **Uninstall rehearsal before the first upgrade:** the rehearsal in section 1b passed but leaves 4 vendor custom fields and the two roles behind; plan their cleanup or document them.
6. **Config check:** API-created Sales Orders on the dev site defaulted to INR (global default currency) while the POS Profile and the POS invoice carry EGP; the POS invoice required an explicit currency. Verify currency on the real POS Profile and company documents before E-14.

Until conditions 1–3 are done, the decision is provisional; the final go/no-go is recorded after the hardware session.
