# 13 Legacy `diva_store` App: Review, Salvage and Retirement

Source: the archive the owner uploaded (`diva_store`, version 1.0.0). Reviewed by reading the code; **nothing was run**. Items marked VERIFY must be confirmed on a staging copy in `TASK-P0-12`.

## 1. What it is
A custom Frappe app, in daily use at the counter. It contains:
- A Desk-based POS built from 22 JavaScript modules injected into the Sales Invoice form (`doctype_js`) plus about 26 KB of CSS that hides Desk elements.
- A standalone Vue 3 pilot called Diva Sale (frappe-ui, Vite) that talks to `api/pos.py`.
- Diva Receiving (Stock Entry, Material Receipt), Quick Add Item with internal EAN-13 barcode generation, Barcode Labels, Price Check, Customer Statement, Collect Payment, a dashboard, five reports and 58/80 mm thermal print formats.
- About 1,800 lines of Python, 4,800 lines of JavaScript and 1,100 lines of Vue. **No automated tests.** The CI "Find tests" step runs `grep -rn "def test"`, which exits with an error when no tests exist, so CI fails by design.

## 2. Findings (severity, location, impact)
### Critical
1. **Prices and discounts are trusted from the browser.** `api/pos.py::_build_sales_invoice` takes each row's `rate` from the client (a missing rate becomes 0) and accepts any `discount_amount`. A tampered or buggy client can sell at zero or any price. There are no MOQ, discount-limit or role checks.
2. **Payments from Diva Sale are probably not recorded (VERIFY).** `submit_sale` appends `payments` rows but never sets `is_pos`, and the standard Sales Invoice payments table applies only to POS-mode invoices. Those invoices likely stay fully outstanding. The Shift Report's by-mode breakdown reads the same table, so it would be empty or wrong.
3. **Held sales create duplicates and ghosts.** In `Sale.vue`, starting a new sale calls `hold_sale` and always inserts a new draft. A resumed draft's `invoice_name` is never sent to `submit_sale`, which inserts a new invoice and leaves the old draft behind. `get_held_invoices` lists every draft with a positive total, not only held sales.
4. **No idempotency anywhere.** `submit_sale`, `hold_sale`, `collect_payment` and `submit_and_pay` can create duplicates after a timeout, retry or double click.
5. **Permission bypass.** `collect_payment` and `create_quick_item` use `ignore_permissions=True` inside whitelisted methods any logged-in user can call, so any user could post a Payment Entry or create Items and Item Prices. `submit_and_pay` loads documents without explicit permission checks.

### High
6. **Prices ignore ERPNext's pricing engine.** `item_lookup.get_selling_price` reads one `Item Price` row and falls back to `standard_rate`. It ignores customer price lists, pricing rules, UOM, validity dates and currency.
7. **UOM is lost.** The cart sends only item code, quantity and rate; `scan` returns the stock UOM. This breaks the dozen-versus-piece design (DEC-20) and UOM-specific barcodes.
8. **Receiving bypasses purchasing.** Diva Receiving posts a Stock Entry (Material Receipt). Supplier purchases then create no payable. The owner buys with goods and invoice together, so this should be a Purchase Invoice with Update Stock (DEC-31). The scan fallback cost of 0 also distorts valuation.
9. **Stock checks read `Bin.actual_qty` only** and ignore reservations (RULE-STOCK).
10. **Module collision.** `diva_store/api.py` and the `diva_store/api/` package coexist; Python imports the package, so `api.py` is unreachable. Two different `get_pos_settings` functions exist.
11. **Bank-type payment modes may fail (VERIFY).** Payment Entries for Bank-type accounts usually require a reference number and date; neither is sent.
12. **Fragile Desk injection.** Many `display:none !important` rules and `*_old.js` dead files. The app's own backlog admits overlay bugs and started the standalone pilot to escape them.

### Medium
13. The settings DocType is defined both in the app and as a fixture, which can conflict on migrate. Payment modes are one comma-separated string.
14. A 2 MB source map, built assets and a zip file are committed inside the package; the git history has no commits.
15. `search_items` runs two extra queries per result row (up to 50 rows) per keystroke, with leading-wildcard `LIKE` searches.
16. Customer outstanding is summed from invoice outstanding amounts, not from the general ledger.
17. Quick Add creates Items and Item Prices without validation; the item code equals the barcode.

### Good (keep the ideas)
Parameterized SQL; no secrets in code; clear comments; use of ERPNext's `set_missing_values()` for Payment Entries; FIFO allocation in Collect Payment; internal EAN-13 barcode generator using GS1's in-store prefix range (20–29); idempotent role and payment-mode setup; broad feature coverage that tells us what the cashiers actually use.

## 3. Salvage and retirement map
The feature-by-feature comparison with POS Next is in `14-feature-decision-matrix.md`.
| Legacy component | Action | Target |
|---|---|---|
| Desk POS (22 modules, CSS) and Diva Sale pilot | **Retire** after POSNext cutover | POSNext (DEC-29) |
| `collect_payment`, customer statement | Rewrite with fixes (permissions, idempotency, reference fields) | Ops: Collect |
| Diva Receiving | Replace | Ops: Receive as **Purchase Invoice with Update Stock**; Stock Entry only for opening stock and non-purchase receipts |
| EAN-13 internal barcode generator | Port with tests; **keep all existing barcodes** | `local-api` item service |
| Barcode Labels, Price Check | Rebuild | Ops: Labels (EAN-13), Items |
| Five Diva reports, dashboard | Replace with standard reports and the Control Room | Phase E reports, Phase PUB Control Room |
| 58 and 80 mm print formats | Superseded by POSNext receipts with QZ Tray | POSNext |
| Roles `Diva Cashier`, `Diva Warehouse Staff` | Update to the role matrix in `07` | E-16 |
| Payment modes Cash, E-Wallet, InstaPay | Rename E-Wallet to Vodafone Cash; add Bank Transfer | E-09 |
| `Diva POS Settings` | Replace with POS Profile and `diva_guard` settings | E-14 |

## 4. Retirement steps (`TASK-E-00`, `TASK-E-14d`)
1. Freeze the legacy app: no new features, bug fixes only for blockers.
2. Back up ERPNext. Restore a copy to staging with the legacy app installed.
3. Verify findings 2, 3 and 11 on staging and record results.
4. Install POSNext and `diva_guard` on staging; run the POS-CHECK list and TEST-44 to TEST-52.
5. Pilot with one cashier for several days alongside the legacy app.
6. Cut over on a quiet day. Keep the legacy app installed but unused for one week as a fallback.
7. Back up again, then uninstall the legacy app. Existing invoices, payments, items and barcodes remain because they are standard ERPNext documents.

## 5. Lessons turned into rules
- Never trust a price, discount or total from a client; recompute on the server (RULE-PRICE, RULE-DISC).
- One held sale is one draft; resume updates the same draft.
- Every state-changing endpoint takes an idempotency key and checks permissions explicitly.
- A payment is real only when ERPNext shows it in the ledger; verify with a test invoice.
- No code ships without tests and a passing CI.
