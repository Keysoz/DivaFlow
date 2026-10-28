# 05a ERPNext Configuration Baseline (Phase E)

ERPNext is simplified by **configuration, not code**. This file is the specification for `TASK-E-01` to `TASK-E-11` and `TASK-E-15` to `TASK-E-17`.

## 1. Principles
- Keep ERPNext's standard stock, accounting, payment and reporting behavior. Simplify the interface around it.
- Allowed: module and workspace visibility, blocked modules per role, Customize Form and Property Setters (hide, default, read-only, mandatory where safe), Role Permission Manager, User Permissions, Print Format Builder, price lists, payment terms, naming series, Stock, Accounts and Selling settings.
- Forbidden: custom Frappe app, Server Scripts, Client Scripts, custom fields, editing core, uninstalling apps (DEC-04).
- Hiding a field never deletes data or removes a process. A hidden field may still be filled by defaults; test it.
- **Never hide without a dependency review:** document identity and status; quantities and units; rates and amounts; required accounting dates; company and currency; tax data; warehouse and stock fields; payment and outstanding amounts; fields required by validation; fields used by an installed app.
- Everything is applied by the idempotent script `infra/erpnext-config/apply.py` through the REST API. Settings live in git as files. The script prints a diff, runs on staging first, and is rerun after every ERPNext upgrade.

## 2. Field and module decision register
Classify every reviewed field and feature as **KEEP, MODIFY, HIDE, OPTIONAL, DEFAULT, DISABLE, INVESTIGATE, DO NOT CHANGE or FUTURE**. Produce `docs/erp-field-register.csv` from the **live site** (never from memory or guesses) with: module and DocType, section, label, verified fieldname, type, current visibility and default, classification, reason, dependencies, method, test case, rollback. Do not invent fieldnames. Mark anything unverified as INVESTIGATE.

## 3. Modules
| Module | Decision | Notes |
|---|---|---|
| Accounting, Stock, Selling, Buying | KEEP | Core |
| Setup and system settings | KEEP, owner and manager only | |
| Manufacturing | HIDE | You do not manufacture |
| HR and Payroll | HIDE | Not needed (DEC-24); no payroll in scope |
| Projects, Quality | HIDE | Not used |
| Assets | HIDE unless equipment tracking is wanted | |
| CRM | HIDE | Chat tools replace it; revisit in Phase G |
| Website, E-commerce, Support | HIDE | |
| Education, Healthcare, others | HIDE if present | Inspect installed apps first |
Hide by blocking modules and workspaces per user or role. Never uninstall an app to simplify navigation. Verify each hidden module has no dependency (for example, accounts reports) before hiding.

## 4. Units, items and barcodes (DEC-20)
- **Stock UOM:** Nos (piece). **Dozen:** UOM with conversion 12. **Purchase UOM and Sales UOM:** Dozen. Item prices are per Dozen. Configure Dozen as whole-number so trading quantities are whole dozens. Piece quantities (single defective pieces, counts, adjustments) use Nos.
- **Barcodes (DEC-32):** internal EAN-13 (GS1 in-store prefix 20–29), as the legacy app generates. Keep all existing barcodes. A dozen (pack) barcode has UOM Dozen; a piece barcode has UOM Nos. Supplier EAN codes are extra barcodes. Barcodes are unique.
- **Item Groups (confirm against the real catalog, OPEN-13):** Accessories and Jewelry (hair accessories, jewelry, bags and similar); Makeup and Cosmetics (face, eyes, lips, nails and similar).
- **Cosmetics:** enable batch and expiry; shade variants for makeup. Accessories: no batch or serial unless needed.
- **Item codes (DEC-32):** existing items keep their codes (the internal EAN-13). New items get an internal EAN-13 as item code. Never reuse a code. Arabic and English names carry the meaning.
- **Simplified Item form:** KEEP code, name, group, UOM and conversion, stock item flag, sales and purchase flags, disabled, barcodes, image, short description, reorder level. HIDE manufacturing and BOM, serial, warranty, weight and shipping, commission, website and similar fields. Keep variant fields for cosmetics shades.
- **Valuation is FIFO (DEC-45).** Audit the existing valuation setting and stock ledger on staging first; never switch blindly or edit the ledger; reconcile with the accountant. Disable negative stock.
- Defaults: warehouse, UOM, company, price list.
- **Warehouses (DEC-49):** Main Inventory, Shop (the counter), Gallery, Returns and Defects (not sellable), In Transit. Sellable flags and chat availability follow OPEN-20.

## 5. Price lists
- Default Standard Buying and Standard Selling lists, per dozen. Tier lists for resellers; customer-specific prices through the Customer's default price list or customer Item Price.
- Validity dates where needed. Price changes restricted to manager and owner. Existing drafts keep their price until refreshed; staff are warned.
- Never hard-code prices in code.

## 6. Purchasing (RULE-PUR)
- Supplier master. Employees see: company name, contact person, phone, address; overseas suppliers also country and currency. Managers see payment terms and outstanding payables. A "China" supplier group is bank-transfer-only (enforced by `diva_guard`).
- **China imports (DEC-47):** Purchase Order, partial Purchase Receipts, Landed Cost Voucher for freight, insurance, customs and clearance, foreign currency with the agreed exchange rate, advances allocated to the final invoice. Confirm exchange-difference treatment with the accountant.
- Purchase Invoice keep: supplier, supplier invoice number and date, posting date, items, quantity, UOM, rate, taxes, totals, paid and outstanding, remarks. Hide project, cost center if unused, landed-cost fields unless used.
- Flow (DEC-31): goods and supplier invoices arrive together, so use **Purchase Invoice with Update Stock**. Hide Purchase Receipt from daily navigation. Turn on supplier invoice number uniqueness.
- Supplier payments through Payment Entry with allocation to invoices; supplier statements and payables reports.

## 7. Sales and customers
- Sales Invoice keep: customer, dates, items, quantity (dozens), UOM, rate, amount, discount, taxes, totals, paid and outstanding, warehouse, remarks. Hide shipping, project, commission, sales-partner and campaign fields if unused.
- Customer: employees see shop name, contact person, phone and address (the preferred courier lives on the reseller profile, not in ERPNext). Managers also see default price list, payment terms, credit limit and outstanding. One record per real customer (never one per invoice). A generic Cash Customer is used only for anonymous counter sales and never overwrites a deliberate selection.
- Discounts use ERPNext fields. Limits per role per RULE-DISC (enforced by local-api; Phase E sets the ERPNext role permission baseline).
- Returns use standard return and credit-note documents; never delete submitted documents.

## 8. Payments, accounts, expenses
- Modes of Payment (DEC-48): Cash, Bank Transfer, Vodafone Cash, InstaPay, ECash, WePay, each with its own account (OPEN-10). Rename the legacy E-Wallet mode to Vodafone Cash and add Bank Transfer.
- Payment Entry for customer receipts and supplier payments, with allocation. Journal Entry restricted to authorized roles.
- Expenses: simple flow through Payment Entry or Journal Entry with an expense account; expense categories tailored to the shop; optional receipt attachment. On the dev site (TASK-E-10) five categories exist under `Indirect Expenses - DD`: Shop Rent, Utilities, Packaging, Marketing and Maintenance; expenses are cash or bank Journal Entries with a cost center.
- Cash tracking: daily cash closing checklist — (1) record the opening cash, (2) add cash receipts from the ledger, (3) subtract cash expenses, (4) compare the expected closing with the counted drawer, (5) record any difference with a reason, (6) attach the count sheet. Sales totals are not cash received; only the cash ledger lines count. `scripts/seed_dev_expenses.py` seeds synthetic expenses and prints this checklist with the reconciled cash and bank movements.
- Reports: cash inflows, outflows and net movement. Daily cash closing checklist. Sales totals are not cash received.

## 9. Taxes
Not applicable (DEC-26): the shop charges no VAT and issues no e-invoices. Keep tax templates empty and hide tax fields after a dependency check. Test that invoices, returns and reports show no tax lines. Revisit if obligations change.

## 10. Permissions
- Owner: System Manager (only the owner).
- Manager: sales, purchase and stock manager roles, accounts access as needed, price list edit.
- Cashier and employees: sales user and stock user only, plus the POS Next vendor role `POSNext Cashier` (required by the approved POS app, DEC-70). Restricted: price lists, large discounts, cancelling submitted documents, Stock Reconciliation, Journal Entry, Chart of Accounts, user management, sensitive reports.
- **POS Next custom permissions (DEC-72):** POS Next installs `Custom DocPerm` rows, which make Frappe ignore the standard `DocPerm` table for those doctypes. `infra/erpnext-config` mirrors the ERPNext standard rows back into `Custom DocPerm` so managers and cashiers keep their documented access; run `make config-apply` after every POS Next install or upgrade. The vendor `POSNext Cashier` and `Nexus POS Manager` rows are never modified.
- **Baseline verified on the dev site (TASK-E-16)** with synthetic accounts `manager@diva.test` and `cashier@diva.test` (`scripts/seed_dev_users.py`): manager can edit price lists, list invoices, payments, Stock Reconciliation and Journal Entry; cashier can create invoices and open the POS but cannot edit price lists, list Stock Reconciliation or Journal Entry, or create users.
- Each staff member has their own ERPNext user (DEC-09). Test every workflow with real employee accounts, not only Administrator.

## 11. Standard reports (saved filters first)
Daily sales; sales by item and by customer; purchases by supplier; gross profit; stock balance by item and warehouse; low stock; customer receivables; supplier payables; outstanding invoices; payment history; cash and bank movements; expenses; returns and cancellations; near-expiry batches. Custom aggregation (Control Room) must reconcile with the standard reports.

## 12. Printing
Sales invoice A4, 80 mm receipt, payment receipt, customer and supplier statements, built with Print Format Builder. Show business identity, number, date, customer, item names, quantities in dozens (the line UOM is printed), rates, totals, discounts, taxes, payment and outstanding. EGP formatting. Arabic right-to-left fonts verified on the real printers. Hide internal fields. Labels are drawn by Diva Ops (not ERPNext).

**Implemented on the dev site (TASK-E-15, partial):** five bilingual Jinja print formats, stored as data and applied by `infra/erpnext-config` (templates in `infra/erpnext-config/print_formats/`): `Diva Sales Invoice A4`, `Diva Receipt 80mm` (Sales Invoice), `Diva Payment Receipt` (Payment Entry), `Diva Customer Statement` (Customer) and `Diva Supplier Statement` (Supplier). They show Arabic primary with an English second line, `EGP` amounts (the EGP currency symbol is set to `EGP`), the line UOM (Dozen or Nos), paid and outstanding amounts and allocated payment references. Both languages live inside the templates because ERPNext print formats are configuration data, not app code, so the `packages/i18n` CI gate does not cover them. Rendering was checked in a browser at A4 and 80 mm widths with synthetic data. Still pending: saved-filter reports, PDF generation with a locally bundled Arabic font (the current PDF path pulls a remote font through Frappe's print CSS), and the real 80 mm printer test (hardware deferred, P0-06).

## 13. Backup, staging and rollback
Back up before every change set. Apply configuration to staging first. Keep configuration files in git. Rollback means reapplying the previous configuration commit. Run a restore test on a separate environment each quarter.

## 14. Acceptance (Phase E)
1. Create an item; find it by code, name and barcode (dozen and piece).
2. Purchase invoice with several items; receive stock using the chosen flow; verify ledger and valuation.
3. Sales invoice with several items; quantities and rates are per dozen; stock leaves once.
4. Full payment, partial payment (back office), and an outstanding invoice appearing in the receivables report.
5. Pay a supplier; payables update.
6. Return or cancellation; verify stock and accounting.
7. Taxes and accounting entries match the accountant's expectation.
8. Employee account cannot change prices, cancel documents or open restricted modules; hidden modules are not visible.
9. Standard reports agree with Control Room summaries.
10. Restore a backup on a test environment; reapply configuration after a simulated upgrade.
Record expected result, actual result, evidence and pass or fail for each.
