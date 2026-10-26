# Appendix: POS Next fit test (TASK-P0-03)

**Status: partial — hardware-dependent checks pending.** The owner will connect the scanner, thermal receipt printer and label printer later (P0-06). Everything that can be verified without the hardware was verified on the disposable dev stack (section 1 of `appendix-erpnext-verification.md`) with synthetic data. No production data or credentials were used (DEC-38).

Date: 2026-10-26. Site: `frontend` (erpnext 16.52.1, frappe 16.53.0).

## 1. What was installed

| Item | Value |
|---|---|
| App | POS Next by BrainWise, repository `BrainWise-DEV/POSNext` (never the exvas "POSNext") |
| Installed commit | `47d2c9a` (branch `develop`, 2026-10-25); app version reports `2.0.0` |
| Latest release tag | `v2.0.0` = commit `e0a52c5` (2026-09-08) — **pin this tag for E-14**, not `develop` (DEC-35) |
| ERPNext 16 compatibility | Install and migrate succeeded on erpnext 16.52.1 / frappe 16.53.0 |
| Custom fields (vendor-owned, DEC-29) | 32: Sales Person (3 commission fields), POS Closing Shift (bank deposit), Journal Entry (7 expense fields + section), Sales Invoice Item (sales_person, customer), Sales Invoice (5: one-time rules, authorized_by/at, sales team, printed, shift), POS Profile (9: expenses, delete, block-sale-beyond-available-qty, cash mode), Sales Order (2: shift, profile), Mode of Payment (wallet) |
| Other records added | Print Format `POS Next Receipt`; roles `POSNext Cashier`, `Nexus POS Manager` and their Custom DocPerms |
| Core modifications | None by this task. The app monkeypatches a few ERPNext classes at import (rounding, packed items) — vendor code, no core files edited |
| Frontend build | `yarn install` + `yarn build` with Node 24.15.0 (Vite 6): succeeded; PWA service worker generated with 53 precache entries (~7 MB) |
| Dev-only workaround | The `pwd.yml` backend image has no Node, so `bench get-app` aborts after cloning; the app was registered in `sites/apps.txt`, installed, then pip-installed (`pip install -e`) and its built assets copied into the frontend container. Production packaging (Dockerfile with Node build stage) is part of E-14 |

Health after install: `GET /pos` → 200, built JS/CSS/manifest/service worker → 200.

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
| 13 | Keyboard-only operation with the owner's key map | **FAIL → required patch** — only F4 (focus search), F8 (customer search) and F9 (payment) are implemented | `pages/POSSale.vue` |
| 14 | Arabic RTL and English switch | **PASS (static), visual pending** — `useLocale.js` sets `dir: rtl`, `LanguageSwitcher.vue`, `ar.csv` has 1,712 entries for about 1,404 `__()` calls | code |
| 15 | Works with no internet while the LAN is up | **Architecture PASS, full-shift test pending** — PWA service worker + workbox precache + `workers/offline.worker.js` + IndexedDB (`dexie`) | build output |
| 16 | No ERPNext core modification, no custom code inside ERPNext | **PASS** — 32 vendor-owned custom fields, 1 print format, no core file edits | see section 1 |
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

1. **Pin the release tag `v2.0.0` (commit `e0a52c5`)** — the fit test installed `develop` (`47d2c9a`). Never auto-upgrade (DEC-35).
2. **Patch set E-14b is required**, not optional: `qty*barcode` multiplier, the owner's full key map with `preventDefault`, and the scan info card. Undo and low-stock tint remain optional.
3. **Hardware session (owner):** Arabic receipt printing (80 mm), QZ Tray, Arabic keyboard layout, visual RTL and English switch, full-shift offline, performance figures, returns and shift closing end to end.
4. **`diva_guard` (E-14a) remains mandatory** for MOQ, discount/PIN, price integrity, full-payment-only and the reserved-stock check (RULE-STOCK).
5. **Uninstall rehearsal** (DEC-35) on a disposable site copy before the first upgrade; document the 32 vendor-owned custom fields first.
6. **Config check:** the dev site defaulted Sales Orders to INR through the API; the POS Profile and documents must carry EGP (the POS invoice did when currency was explicit). Confirm currency on the real POS Profile.

Until conditions 1–3 are done, the decision is provisional; the final go/no-go is recorded after the hardware session.
