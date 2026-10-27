# Appendix: POS Next fit test (TASK-P0-03)

**Status: complete for the agent side — hardware validation deferred to purchase (owner, 2026-10-27); uninstall rehearsals done; pinned `v2.0.0` re-run and post-patch smoke done.** The owner deferred the scanner, thermal receipt printer and label printer to a later session (P0-06) and authorised synthetic data instead of a production-data copy (owner, 2026-10-26; recorded in DEC-68). Everything that can be verified without the hardware was verified on the disposable dev stack (section 1 of `appendix-erpnext-verification.md`) with synthetic data. No production data or credentials were used (DEC-38).

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
| Reserved-stock block | **PASS** — blocked while fully reserved (`NegativeStockError` in the API response; the failure is not persisted in Error Log); after cancelling the reservation the same invoice submitted, stock 96 → 72, the other order's 24 stayed reserved |
| Offline / PWA | **LIMITATION** — the service worker is served at `/assets/pos_next/pos/sw.js` (no `Service-Worker-Allowed` header), so its scope cannot control `/pos`; `/pos-sw.js` is 404 at v2.0.0. The manifest compounds it: `scope: /assets/pos_next/pos/` with `start_url: /pos`. The develop build adds a root-scope copy (`www/pos-sw.js`) registered with `scope: "/pos"`. Needs a patch or a newer release before offline is claimed. |
| Uninstall rehearsal | uninstall succeeds, `/pos` 404; **10 custom fields** and the two roles remain (the vendor removes only 2 explicitly; the rest depend on module cleanup). Reinstall restores 21 fields and `/pos` 200. |

**Verdict impact:** the pin condition is satisfied for tag pinning, but `v2.0.0` is code `1.17.0`: no global F-keys, fewer fields and an offline scope gap. The patch set (section 1e) fixed `qty*barcode` and offline; the smoke subset was re-run on the patched build (section 1f). Hardware validation is deferred until the owner buys the hardware.

### 1d. Automated browser checks (2026-10-27)

Playwright (Chromium headless) against `http://localhost:8080/pos` on the pinned v2.0.0 build, signed in as Administrator, POS Profile `P003 POS`, shift opened through the UI (500 cash).

| Check | Result |
|---|---|
| POS Profile visibility | **Setup finding**: the app lists only profiles whose `applicable_for_users` contains the user. A profile created without that row shows "No POS Profiles available"; adding Administrator fixed it. Note this for E-14. |
| Shift open through the UI | PASS — welcome screen → profile → opening balance → sale screen with the shift timer. |
| Barcode scan (EAN-13, Dozen) | PASS — the scan opens the "Select Unit of Measure" dialog (Dozen E£ 1,440 / Nos E£ 0), adding Dozen gives 1 × Dozen at E£ 1,440; a second scan raises the line to 2 (E£ 2,880). The product card stock drops 72 → 60 → 48 as the cart grows. |
| Scan info on screen | **Partial**: the dialog shows the item name, code, per-UOM prices and the stock is on the item card; a success toast names the added line. There is no single combined scan card, and two defects were visible: the **"Nos" UOM appears twice** (the item's UOM table includes the stock UOM row) and the **quantity input is borderless with a transparent background**, so its centered value is easy to miss (the DOM value is 1). |
| Arabic / RTL | **PASS (visual)**: with the user's language Arabic the document direction is `rtl` and the header, icon rail, panels, badges, icons and totals all mirror correctly. Untranslated strings: **"Shift History"**, the **item-search placeholder**, and the unit name "Nos" (UOM data, not a UI key). The header language control shows العربية. |
| Offline | **FAIL confirmed in a real browser**: with the network off, reload fails (`ERR_INTERNET_DISCONNECTED`). The app is **not offline-capable at v2.0.0**, despite its "Data is ready for offline use" toast — consistent with the service-worker scope gap in section 1c. |
| Runtime errors | `pos_next.api.pos_profile.get_receivable_accounts` raises **`NameError: name 'cint' is not defined`** (customer/credit UI); the socket.io connection is refused in this dev setup (realtime unavailable); the vendor page still references `/assets/nexus_demo` demo-banner files, which return 404 (harmless; note for cleanup); `pos_next.api.qz.get_certificate` returns 417 (QZ print certificate, relevant to the hardware session). |

**Verdict impact:** the browser pass removes the visual-RTL uncertainty and adds concrete UI defects to the patch list (duplicate UOM option, quantity display, untranslated keys, the `get_receivable_accounts` bug). It also confirms that v2.0.0 cannot be sold as offline-capable. Hardware-only items (physical scanner, 80 mm receipt, label printer) still need the owner session.

### 1e. Patch set applied and verified (2026-10-27)

The tracked patch set lives in `infra/posnext-patches/` (**11 patches** on tag `v2.0.0`, applied to the dev site and verified in the browser):

| Fix | Verified result |
|---|---|
| `cint` import for `get_receivable_accounts` | API returns 200; the `NameError` disappeared from the console |
| UOM dialog de-duplication | the dialog now lists **one** Nos and Dozen |
| Quantity input styling | the field has a visible border/background |
| `qty*barcode` multiplier | scanning `3*2000000000015` pre-fills quantity 3 and adds 3 Dozen (E£ 4,320) |
| Arabic keys | item-search placeholder and "Shift History" translated; `dir=rtl` (native review still required) |
| Offline (scope, fallback, absolute precache, workbox import, injected manifest entry, client claim) | **verified with a cache-proof protocol**: the controller is non-null after the first load; every precache URL is absolute; with the frontend **stopped**, an **unvisited** `/pos/<random>` path and a reload both serve the app shell (the sign-in screen appears because authentication needs the server) |

Notes for E-14 packaging:
- The worker is served from the site root (`/pos-sw.js`, copied from `public/pos/sw.js` by the build) so it can scope `/pos`; the precache URLs **and the workbox import** must stay absolute, the injected `manifest.webmanifest` entry included, and `injectRegister` stays `false` (main.js is the only registrar).
- After deploying the worker, clear the Frappe website cache — a stale `/pos-sw.js` otherwise persists (observed during the test), and serve it with `Cache-Control: no-cache`.
- Full offline **selling** (cached session/shift) still needs a browser/hardware-session check; the shell and assets are proven. An early check that reported "offline works" was a browser HTTP-cache false positive; the cache-proof protocol above replaced it.

Remaining E-14b items (not patched yet): the owner's full key map (F1–F10 and Ctrl combinations; at v2.0.0 there are none) and a single combined scan info card (the dialog + toast remain). Receipt printing and QZ Tray validation need the hardware, which the owner will buy later (2026-10-27); they are deferred, not blocking.

### 1f. Post-patch smoke re-run (2026-10-27)

After applying the 10-patch set and rebuilding the assets:

- **POS invoice** `ACC-SINV-2026-00003` submitted: EGP, 1 Dozen → `stock_qty` 12 Nos, grand total and paid 1,440.
- **Reserved-stock block**: `SAL-ORD-2026-00005` reserved all 72 Nos (full); the same POS invoice was rejected with `NegativeStockError`. After cancelling the order the invoice submitted; Bin moved 72 → 60 Nos, reserved 0.
- The patch set does not change install/uninstall behaviour; the rehearsals in sections 1b/1c stand.
- The user's language was restored to English after the Arabic checks; the dev site keeps the synthetic `P004*` data.

### 1g. Key map and scan card (patch 11, 2026-10-27)

Verified with Playwright on the patched build:

- **Key map:** F1 opens the shortcut help; F2 focuses the customer search; F3/F4/F5 open the last-line editor (quantity and discount — the vendor has **no line-note field**, so F5 opens the same editor and a note feature would be a separate change); F6 removes the last line; F7 drafts; F8 payment (asks for a customer when none is selected); F9 prints the last invoice or warns before one exists; F10 clears the cart (with confirmation); Ctrl+F focuses the item search; Ctrl+Delete clears; Ctrl+Z undoes the last scan even while the search field has focus; Ctrl+R opens the return dialog on the main POS view.
- **Dialog guard:** shortcuts are ignored while a **registered** dialog is open (payment, drafts, return, clear cart, offers), and while the help overlay is up (Escape closes it). The edit-item and scan dialogs are not registered yet, so F6 can still act behind them — a known gap to close when those dialogs are migrated.
- **Scan card:** every scan shows the item name, code, price per Dozen **from the price list** (E£ 1,440 for the test item — an earlier ×12 error was fixed), stock in its UOM, and the quantity added in the scanned UOM; it hides after four seconds and focus returns to the barcode field.
- New Arabic keys were added for the card and the shortcut labels after the glossary review; a spot-check by the owner is recommended for wording.

Remaining: hardware validation (80 mm receipt, QZ Tray, Arabic keyboard, full offline shift) and, if the owner wants F5 to be a true note field, that feature.

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
| 14 | Arabic RTL and English switch | **PASS (static and visual browser check, section 1d)** — `dir=rtl`, layout mirrors; three untranslated strings found | code + screenshots |
| 15 | Works with no internet while the LAN is up | **FAIL at v2.0.0 (browser-confirmed, section 1d); the SW scope cannot control `/pos`** — PWA service worker + workbox precache + `workers/offline.worker.js` + IndexedDB (`dexie`) | build output |
| 16 | No ERPNext core modification, no custom code inside ERPNext | **PASS** — 37 vendor-owned custom fields (at the tested build), 1 print format, no core file edits | see section 1 |
| 17 | Performance (UI < 100 ms; search/barcode < 500 ms; large invoices) | **Pending (browser)** | — |
| 18 | Scan info card (name, code, price per dozen, stock, qty added, focus returns) | **Partial → patch (E-14b)** — the browser check (section 1d) shows the scan dialog, item card stock and a toast with the added line, but there is no combined card; the "Nos" option is duplicated and the qty input is borderless (easy to miss) | code + browser |
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
| Keyboard shortcuts — "map unverified" | **None at the pinned v2.0.0**; F4/F8/F9 on develop only (section 1c) → required patch (full owner key map) |
| Offline — "yes (tested)" | Architecture present; at v2.0.0 the service-worker scope gap applies (section 1c); full-shift test pending |

## 4. Verdict (provisional)

**Provisional GO for POS Next on ERPNext 16**, subject to these conditions before E-14 starts:

1. **Pin done: `v2.0.0` re-run executed (section 1c).** `v2.0.0` is code `1.17.0` (vendor tag/version mismatch) with 21 fields, no global F-keys and an offline service-worker scope gap. Before E-14, re-run the smoke subset on the **patched** pinned build; never auto-upgrade (DEC-35).
2. **Patch set E-14b is required**, not optional: `qty*barcode` multiplier, the owner's full key map with `preventDefault`, the scan info card, and a root-scope service worker for offline. Undo and low-stock tint remain optional. (At `v2.0.0` there are no global F-key handlers at all; the patch set grows.)
3. **Hardware session (owner):** Arabic receipt printing (80 mm), QZ Tray, Arabic keyboard layout, visual RTL and English switch, full-shift offline, performance figures, returns and shift closing end to end.
4. **`diva_guard` (E-14a) remains mandatory** for MOQ, discount/PIN, price integrity, full-payment-only and the reserved-stock check (RULE-STOCK).
5. **Uninstall rehearsal before the first upgrade:** the pinned rehearsal in section 1c leaves **10 vendor custom fields** and the two roles behind; plan their cleanup or document them. (`custom_brands_table` is not an orphan: it is removed with the `POS Brands Detail` doctype.)
6. **Config check:** API-created Sales Orders on the dev site defaulted to INR (global default currency) while the POS Profile and the POS invoice carry EGP; the POS invoice required an explicit currency. Verify currency on the real POS Profile and company documents before E-14.

Conditions 1 (pin) and 2 (patches) are done; condition 3 (hardware) is deferred to the owner's purchase. The baseline is approved (DEC-70): the decision is final for the software, subject to hardware validation when the hardware arrives.
