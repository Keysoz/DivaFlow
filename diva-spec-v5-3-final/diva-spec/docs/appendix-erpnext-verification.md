# Appendix: ERPNext verification

Evidence for the ERPNext tasks. Created by TASK-P0-04a (2026-10-26); TASK-P0-04 adds the verification findings below.

## 1. Disposable development stack (TASK-P0-04a)

Built by `scripts/start-dev-erpnext.sh`: it clones `frappe/frappe_docker` into `$HOME/frappe_docker` (or a directory you pass) and runs `docker compose -f pwd.yml up -d`. This is a **disposable demo**: never put real business data in it. The production ERPNext is installed on the store VM in TASK-E-00a.

The `pwd.yml` site starts **without setup-wizard data** (no company, UOMs, item groups or warehouses). TASK-P0-04 bootstrapped it with ERPNext's own fixtures (`erpnext.setup.setup_wizard.operations.install_fixtures.install("Egypt")`) and created a dev company `Diva Dev` (abbr `DD`, EGP, country Egypt). A bare site cannot be used for stock, barcode or payment checks.

| Item | Value |
|---|---|
| Date of record | 2026-10-26 |
| Start command | `bash scripts/start-dev-erpnext.sh` |
| Stop command | `docker compose -f ~/frappe_docker/pwd.yml down` |
| URL | `http://localhost:8080` (port 8080 as required by P0-04a) |
| Site name | `frontend` (default in `pwd.yml`) |
| Login | `Administrator` / `admin` — the documented disposable dev default printed by the start script |
| Image pin | `frappe/erpnext:v16.52.1` (already tagged to the major version 16 in `pwd.yml`; no change was needed) |
| Image digest | `sha256:eb1c22d2bb926ed97352b63334507bf0297f1ca1244b406e3f30869ca5d0092b` |
| Database | `mariadb:11.8` (`sha256:f16d7a344413e519dff518f27bdb221388f84b0d274c97c4fb5f2cb0dc1b34fa`) |
| Cache and queue | `redis:6.2-alpine` (`sha256:592b215e9287182f11ba9d7c229dc0ba312bb900a016ea65ae378b0127567319`) |
| Host | Linux 6.12.100+deb13-amd64, Docker 29.9.2, Docker Compose v5.6.1 |

### Recorded versions

```
$ docker exec frappe_docker-backend-1 bench version
erpnext 16.52.1  ()
frappe 16.53.0  ()

$ docker exec frappe_docker-backend-1 bench --site frontend list-apps
frappe  16.53.0 UNVERSIONED
erpnext 16.52.1 UNVERSIONED
```

The `UNVERSIONED` label is normal for a locally built app inside the image; the versions in the first command are authoritative.

### Health evidence

```
$ curl -fsS http://localhost:8080/api/method/ping
{"message":"pong"}

$ curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/login
200

$ docker ps --format "{{.Names}} {{.Ports}}" | grep 8080
frappe_docker-frontend-1 0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp
```

## 2. Verification findings (TASK-P0-04)

Performed 2026-10-26 on the disposable dev site (`frontend`) of section 1 — version `erpnext 16.52.1`, `frappe 16.53.0`. **This is not the live site**: DEC-63 has no staging copy; TASK-E-00a installs production ERPNext on the store VM and TASK-E-01 re-runs these checks on the live site. The findings here are version-level and expected to hold. Arabic print/receipt behaviour is out of scope here (TASK-P0-03 and TASK-E-15).

| # | Capability | Finding | Evidence |
|---|---|---|---|
| 1 | Version and apps | ERPNext 16.52.1, Frappe 16.53.0; only `frappe` and `erpnext` installed | section 1 |
| 2 | Stock reservation | **Off by default** (`Stock Settings.enable_stock_reservation = 0`). After enabling it and `auto_reserve_stock`, a submitted Sales Order with `reserve_stock = 1` creates a `Stock Reservation Entry` (`status = Reserved`). `allow_partial_reservation = 1` by default: a second order for 120 Nos against 96 free Nos was **partially reserved (96)** with status `Partially Reserved`. **The counter is blocked (RULE-STOCK 5):** a Material Issue of 10 Nos against fully reserved stock failed with `NegativeStockError` ("As the full stock is reserved for other transactions, you're not allowed to consume the stock"). Native reservation therefore blocks competing stock movements; the backend-hold fallback is not needed for stock. Confirm the POS Next counter path (Sales Invoice with update stock) in TASK-P0-03. | `MAT-SRE-2026-00001` (24 Nos `Reserved`), `MAT-SRE-2026-00002` (96 Nos `Partially Reserved`), `MAT-STE-2026-00002` (rejected) |
| 3 | Item Barcode with UOM | `Item Barcode` has `barcode`, `barcode_type`, `uom`. One item can carry several barcodes: a Dozen barcode (`uom = Dozen`) and a Nos barcode (`uom = Nos`). | item `P004-DOZEN`, barcodes `2000000000015` (Dozen) and `2000000000022` (Nos) |
| 4 | Barcode validation | Barcodes flagged `EAN` must be valid EAN-13 (checksum checked). A barcode already used on another item is rejected globally. | `InvalidBarcode: Barcode … is not a valid EAN code`; `ValidationError: Barcode 2000000000015 already used in Item P004-DOZEN` |
| 5 | Barcode lookup (adapter path) | `GET /api/resource/Item Barcode?filters=[["barcode","=","2000000000015"]]` returns the row; fetch the row by name to read `parent` (item) and `uom`. Child tables (any `istable` doctype, e.g. Item Barcode, Customer Credit Limit, Payment Terms Template Detail) return only `name` when `fields` is passed, while parent doctypes honour `fields`; for child rows, read the full row. | `{"barcode":"2000000000015","parent":"P004-DOZEN","uom":"Dozen"}` |
| 6 | Dozen whole-number UOM | ERPNext 16 does **not** ship a Dozen UOM (239 UOM fixtures in `uom_data.json`, none named Dozen). Create `UOM` `Dozen` with `must_be_whole_number = 1`; give the Item `uoms = [{uom: Dozen, conversion_factor: 12}]`. A transaction at 2 Dozen became `stock_qty = 24 Nos`; a 1.5 Dozen line was rejected natively. | `UOMMustBeIntegerError: Quantity (1.5) cannot be a fraction … disable Must be Whole Number in UOM Dozen` |
| 7 | Payment Terms | `Payment Term` (name, `invoice_portion`, `due_date_based_on`, `credit_days`) + `Payment Terms Template` (child `Payment Terms Template Detail`) work. A 30%/70% template produced a correct payment schedule on the Sales Order. | schedule: 864 due 2026-10-27 (30%), 2,016 due 2026-11-26 (70%) for a 2,880 order. **Amounts are in the document currency (INR) because the API-created Sales Orders defaulted to the site's global default; the POS invoice in `appendix-posnext-fit-test.md` is EGP.** |
| 8 | Credit limit | `Customer.credit_limits` (child `Customer Credit Limit`: `company`, `credit_limit`, `bypass_credit_limit_check`). Submitting a Sales Order above the limit is **blocked** natively. | customer limit 5,000; 14,400 order rejected: `ValidationError: Please contact your administrator to extend the credit limits for P004 Reseller.` |
| 9 | REST endpoints | Session login, `GET/POST/PUT/DELETE /api/resource/<doctype>`, filters, `frappe.client.get_count`, `frappe.client.get_value`, `frappe.client.submit` all work. Verified on Item, Item Barcode, Customer, Sales Order, Sales Order Item, Stock Entry, Bin, Stock Reservation Entry, Payment Term(s) Template, Price List, Fiscal Year, Stock Settings, UOM. Session auth was used here; API-key token auth (`Authorization: token <key>:<secret>`) belongs to the adapter contract tests (TASK-E-12). List endpoints page at about 20 rows by default; use `limit_page_length=0` for a full read. | see commands below |
| 10 | Available-to-promise (`Bin`) | `Bin.reserved_qty` follows the reserved voucher quantity, not the SRE: with 120 Nos actual and SREs of 24 + 96, `Bin` showed `reserved_qty = 144` and `projected_qty = -24`. Compute ATP from `Stock Reservation Entry.reserved_qty` (24 + 96 = 120), not from `Bin.projected_qty`. | `Bin` read |

### Commands and raw results (selected fields shown)

```
# login (session cookie)
POST /api/method/login                       -> {"message":"Logged In"}
GET  /api/method/frappe.auth.get_logged_user -> {"message":"Administrator"}

# reservation: Sales Order with reserve_stock=1, 2 Dozen at 1,440 EGP
POST /api/resource/Sales Order               -> data.name SAL-ORD-2026-00001 (draft)
POST /api/method/frappe.client.submit        -> {"docstatus":1}
GET  /api/resource/Sales Order/SAL-ORD-2026-00001
  data: {"grand_total":2880.0,"reserve_stock":1,
         "items":[{"qty":2.0,"uom":"Dozen","stock_qty":24.0,"stock_reserved_qty":24.0}],
         "payment_schedule":[{"payment_term":"P004 Advance 30","payment_amount":864.0,"due_date":"2026-10-27"},
                             {"payment_term":"P004 Net 30","payment_amount":2016.0,"due_date":"2026-11-26"}]}

GET /api/resource/Stock Reservation Entry
    ?filters=[["voucher_no","=","SAL-ORD-2026-00001"]]&fields=["name","reserved_qty","status"]
  -> [{"name":"MAT-SRE-2026-00001","reserved_qty":24.0,"status":"Reserved"}]

# partial reservation (96 Nos free after the first order)
GET /api/resource/Stock Reservation Entry
    ?filters=[["voucher_no","=","SAL-ORD-2026-00002"]]&fields=["name","reserved_qty","status"]
  -> [{"name":"MAT-SRE-2026-00002","reserved_qty":96.0,"status":"Partially Reserved"}]

# fractional dozen
POST /api/resource/Stock Entry {"qty":1.5,"uom":"Dozen", ...}
  -> UOMMustBeIntegerError: Row 1: Quantity (1.5) cannot be a fraction.

# counter blocked by reservations (Material Issue 10 Nos against fully reserved stock)
POST /api/resource/Stock Entry {"stock_entry_type":"Material Issue","qty":10,"uom":"Nos", ...}
POST /api/method/frappe.client.submit
  -> NegativeStockError: "... As the full stock is reserved for other transactions,
     you're not allowed to consume the stock."
```

### Test records created on the disposable site (safe to discard)

Company `Diva Dev` (EGP, fiscal year `2026-2027`); UOM `Dozen` (whole number); item `P004-DOZEN` (Nos stock UOM, Dozen conversion 12, two barcodes); customers `P004 Reseller` (credit limit 5,000) and `P004 NoLimit`; payment terms `P004 Advance 30` / `P004 Net 30` and template `P004 30-70`; price list `Standard Selling`; stock entries `MAT-STE-2026-00001` (120 Nos received) and `MAT-STE-2026-00002` (Material Issue probe, rejected — no stock moved); sales orders `SAL-ORD-2026-00001/2` submitted and `SAL-ORD-2026-00003` rejected by the credit limit; reservation entries `MAT-SRE-2026-00001/2`. `Bin` after reservations: actual 120, reserved 144, projected -24. Stock Settings was changed to `enable_stock_reservation = 1` and `auto_reserve_stock = 1`. Currency note: the API-created Sales Orders defaulted to INR (site global default) while the price list and the POS Profile are EGP; the currency was set explicitly on the POS invoice in `appendix-posnext-fit-test.md`. Confirm currency defaults on the real site at E-01.

### Gaps for later tasks

- Live-site re-check (production on the store VM; there is no staging copy, DEC-63): TASK-E-01.
- API-key token authentication and the adapter's exact call shapes: TASK-E-12 contract tests (this task used session auth).
- POS Next counter path against reservations (Sales Invoice with update stock): TASK-P0-03.
- Delivery Note and Sales Invoice creation, deposit advances and Payment Entry allocation: TASK-E-12 and TASK-O-10.
- Arabic receipts, 80 mm print formats: TASK-P0-03 and TASK-E-15.

## 3. E-01 baseline (provisional, dev site)

Date 2026-10-27. Source: the disposable dev site — no production site exists yet (DEC-63; TASK-E-00a installs it on the store VM).

- **Apps:** frappe 16.53.0, erpnext 16.52.1, pos_next 1.17.0 (pinned tag `v2.0.0` + the 11 tracked patches).
- **Site:** company `Diva Dev` (abbr `DD`), default currency EGP, country Egypt, fiscal year `2026-2027` (2026-07-01 → 2027-06-30).
- **Field register:** `docs/erp-field-register.csv` — 28 core doctypes, **2,028 rows** (2,016 DocField + 12 Custom Field), generated from the live schema **and** the installed custom fields (no invented fieldnames). It includes the 12 vendor POS Next fields that live on these doctypes (21 exist across all POS Next doctypes).
- **Classification:** every row carries `classification` = `keep` with a `reason`; TASK-E-02/E-03 change the rows they act on. The `source` column distinguishes schema from custom fields.
- **Repeatable:** `scripts/gen_field_register.py` (credentials from env) regenerates the file.
- **Provisional:** re-run this register at TASK-E-00a against the production site and diff; only then is it the authoritative baseline.

## 4. Configuration applied (E-03/E-02, dev site)

Date 2026-10-27. `infra/erpnext-config/apply.py` (idempotent, dry-run by default) with `config.yaml`; credentials from the environment.

- **Dry run (first pass):** property setters hiding `tax_id` and `taxes_and_charges` on Sales Invoice and Sales Order (DEC-26: no VAT); hide the `Manufacturing` workspace (E-02); **singles**: `Stock Settings.allow_negative_stock = 0`, `enable_stock_reservation = 1`, `auto_reserve_stock = 1` (E-04); **records**: `UOM Dozen` whole-number, item groups `Accessories` and `Cosmetics`, price list `Wholesale` (E-04/E-05).
- **E-04/E-05 first pass:** 3 changes — the two item groups and the `Wholesale` price list (the stock singles and the UOM already matched). **Applied**, then the same dry run again: **0 changes** (14 no-op/missing) — idempotency proven. Reapply after every upgrade (E-03 acceptance).
- `HR` and `Payroll` workspaces do not exist on this site; the config reports them as `missing` and skips them. Per-role refinement lands with the roles/users task (E-16).
- Workspaces are hidden globally (`is_hidden`); no core code or custom fields were created. Batch/expiry per item (E-14c), per-tier prices and price-edit permissions (E-05/E-16) remain.

## 5. Bulk synthetic data (E-06/E-07/E-08/E-09, dev site)

Seeded idempotently with `scripts/seed_dev_data.py` (credentials from env; synthetic only):

- **Warehouses (DEC-49):** Main Inventory, Shop, Gallery, Returns and Defects added beside Stores / WIP / Finished Goods / Goods In Transit.
- **Items + barcodes (E-06):** 12 items (6 Accessories, 6 Cosmetics) with Dozen and Nos EAN-13 barcodes (e.g. `BULK-ACC-01`: `2100001000011` Dozen, `2100001000028` Nos) and a per-Dozen selling price.
- **Opening stock (E-07):** Stock Reconciliation (Opening Stock) posted 120 Nos per item into Main Inventory.
- **Purchasing (E-08):** 2 suppliers and Purchase Invoice `ACC-PINV-2026-00001` (bill `BULK-PI-01`) with Update Stock — two stock ledger movements of +60 Nos each (5 Dozen).
- **Sales (E-09):** 5 customers; a paid POS invoice (Cash) and a credit Sales Invoice with `outstanding_amount = 2,496`; six payment modes (Cash, Bank Transfer, Vodafone Cash, InstaPay, ECash, WePay) mapped to `Cash - DD` and a new ledger account `Diva Bank - DD`.
- Bin check after all movements: `BULK-ACC-01` = 168 Nos (120 opening + 60 purchase − 12 sold).
- Pending for the full tasks: FIFO valuation audit, supplier payments/payables, receivable report reconciliation, China import flow (E-08b), expenses (E-10).

## 6. Roles and permissions (E-16, dev site)

Seeded with `scripts/seed_dev_users.py` (synthetic accounts; password from `DIVA_TEST_PASSWORD`, never committed):

- `manager@diva.test`: Sales Manager, Sales Master Manager, Purchase Manager, Stock Manager, Accounts User.
- `cashier@diva.test`: Sales User, Stock User, POSNext Cashier (vendor role required by POS Next).
- **Finding:** POS Next ships `Custom DocPerm` rows for 15 doctypes. Frappe ignores the standard `DocPerm` table for a doctype once custom rows exist, so installing POS Next removed Sales Invoice and Journal Entry access from `Accounts User` (and Item/Customer/Warehouse access from stock/sales roles). `infra/erpnext-config` now mirrors the standard rows into `Custom DocPerm`; POS Next-only roles are never touched and a second run reports 0 changes.
- **Verified with real logins (not Administrator):** manager can edit price lists, list Sales Invoice, Payment Entry, Stock Reconciliation and Journal Entry; cashier can create a draft Sales Invoice and open the POS (POS Profile) but cannot write price lists, list Stock Reconciliation or Journal Entry, or create users.
- **Known gap:** the vendor `POSNext Cashier` role includes cancel on Sales Invoice (POS void). The rules engine and local-api must keep void approval with a manager (TASK-E-14a); this is not yet enforced at the ERPNext permission layer.

## 7. Print formats (E-15, dev site)

- Five bilingual Jinja print formats are stored as `Print Format` data and applied by `infra/erpnext-config` (idempotent; re-run 0 changes): `Diva Sales Invoice A4`, `Diva Receipt 80mm` (Sales Invoice), `Diva Payment Receipt` (Payment Entry), `Diva Customer Statement` (Customer) and `Diva Supplier Statement` (Supplier).
- Templates live in `infra/erpnext-config/print_formats/` and show Arabic primary with English second lines, `EGP` amounts (currency symbol set to `EGP`), the line UOM (Dozen or Nos), totals, paid/outstanding and payment allocations.
- Verified with synthetic data: A4 and 80 mm browser renders (`ACC-SINV-2026-00007`, 2 Dozen × EGP 1,248 = EGP 2,496, unpaid) show the correct customer, item, UOM, amounts and RTL direction; the payment receipt renders `ACC-PAY-2026-00001`.
- Statements list posted invoices and payments with totals/outstanding and accept optional `from_date`/`to_date` parameters; verified for `Bulk Customer 02` (EGP 2,496 outstanding) and `Bulk Supplier 1` (purchase invoice `ACC-PINV-2026-00001`).
- Pending: saved-filter reports, PDF generation with a locally bundled Arabic font (wkhtmltopdf currently pulls a remote font via Frappe's print CSS and fails without internet) and the real 80 mm printer test (hardware deferred).

## 8. Expenses and cash closing (E-10, dev site)

- Five expense ledger accounts under `Indirect Expenses - DD`: Shop Rent, Utilities, Packaging, Marketing and Maintenance.
- `scripts/seed_dev_expenses.py` (idempotent, synthetic) posts five cash/bank expenses through Journal Entries (cash entries for four, a bank entry for Marketing with a reference number and date).
- Daily cash closing cross-checked against two independent sources on this dataset: cash receipts come from sales-invoice payments and customer receipts (1,624), expenses from the seeded list (1,490.50), and the expected closing is compared with the GL (8,140 + 1,624 − 1,490.50 = **8,273.50**); bank 0 + 500 − 500 = **0**. Every expense account has exactly its expected debit and zero credit, so a double-post or a wrong cash figure fails the script (exit 1).
- The script also prints the six-step closing checklist (opening, receipts, expenses, expected closing, counted difference, count sheet); sales totals are not treated as cash received.
- Pending: receipt attachment workflow in Ops, expense categories editing and the Ops expenses screen (E-13).


## 9. diva_guard server rules and manager PIN (E-14a, dev site)

- Custom app `apps/diva_guard` (minimal: hooks, settings/approval doctypes, `Diva Product Rule`; no ERPNext core changes; the only custom field is the owner-approved `Item.custom_barcode`, DEC-78). Installed with `scripts/install_diva_guard.sh`, which also installs `packages/rules-engine` into the bench environment.
- Rules enforced on Sales Invoice validate for every client: MOQ/step in Dozen, authoritative price-list rate, effective discount (5% cashier / 15% manager), manager PIN approval, counter credit/partial payment for non-managers (including `is_pos=0`), available stock (`actual_qty − reserved_qty`).
- Manager PIN stored only as PBKDF2-HMAC-SHA256 (at least 260,000 iterations, random salt) in `Diva Guard Settings`; the approval API is rate-limited (five attempts per five minutes) and returns a 10-minute, single-use token (only its SHA-256 hash is stored) sent as `X-Diva-Override-Token`. Consumption is serialised with a Redis lock and is idempotent for the same voucher; replay, expiry and another user’s token are rejected.
- `scripts/test_diva_guard.py` with real cashier/manager logins passes all checks: MOQ rejected; compliant sale created and submitted; cashier 10% discount blocked at submit; manager 10% accepted; PIN-token discount submitted and replay blocked; wrong-user and expired tokens rejected; approval below the actual discount rejected; counter partial payment blocked; rate above the price list blocked; Nos line priced from Dozen; negative quantity and free items rejected; cashier credit invoice blocked while a manager credit invoice is accepted.
- Remaining: POS Next PIN dialog and header (E-14b/E-14d), FEFO/expired batches (E-14c), production install and owner PIN rotation.

## 10. China import in EGP (E-08b, dev site)

Owner decision DEC-75: the Chinese supplier is treated like an Egyptian supplier; item prices are EGP and there is no foreign-currency or exchange-rate handling. `scripts/seed_china_import.py` (idempotent) creates:

- Supplier group `China` and supplier `China Supplier 1` with EGP currency.
- Purchase Order `PUR-ORD-2026-00002` for 10 Dozen at EGP 1,200, fully received through two partial Purchase Receipts (6 + 4 Dozen) and fully billed.
- Landed Cost Voucher `MAT-LCV-2026-00002` for EGP 1,200 freight/customs, allocated by amount across both receipts.
- Purchase Invoice `ACC-PINV-2026-00006` for EGP 12,000, paid by two bank payments of EGP 4,800 and EGP 7,200.
- Verified: stock +120 Nos, stock value +13,200 (12,000 goods + 1,200 landed cost), PO 100% received and billed, invoice outstanding 0, supplier GL balance 0, two payment history rows.
- The first run created the documents; a second run changed nothing and still reported all checks OK.

## 11. FEFO and expired batches (E-14c, dev site)

- `Stock Settings.pick_serial_and_batch_based_on = Expiry`, `enable_serial_and_batch_no_for_item = 1`, `auto_create_serial_and_batch_bundle_for_outward = 1`; ERPNext's auto-batch query excludes batches with `expiry_date < today` and orders by expiry.
- `scripts/seed_batches.py` creates `BULK-COS-BATCH-01` with batches expiring 2026-11-15 (earlier) and 2027-01-15 (later), and `BULK-COS-EXPIRED-01` with an already expired batch, each with opening stock through Stock Reconciliation (batch fields).
- `scripts/test_fefo.py` with the cashier account submitted a sale without naming a batch: the Serial and Batch Bundle selected `BATCH-COS-2026-00001` (2026-11-15), the earliest available; the expired item could not be submitted (mandatory batch error, no available non-expired batch).
- **Migration SOP before cutover:** freeze the item, count physical stock by batch/expiry, create `Batch` records, enable `has_batch_no`/`has_expiry_date`, post a Stock Reconciliation per batch with `use_serial_batch_fields=1`, reconcile Bin and batch quantities, test a sale (FEFO) and a return. If ERPNext refuses to enable batch tracking while unbatched stock exists, reconcile the item to zero first, enable tracking, then post the batch-wise opening stock. Rollback requires zeroing stock before disabling batch tracking.
- **POS UI caveat:** the server-side FEFO/expired block is verified; whether POS Next v2.0.0 exposes or auto-picks batches must be confirmed on staging in E-14b/E-14d.
- Expired exclusion compares batch expiry with today, not the posting date; backdated returns/credits need a manual check.

## 12. Selling dashboard chart error (ERPNext 16.52.1, fixed by data)

Opening `dashboard-view/Selling` failed with `TypeError: cannot unpack non-iterable NoneType object` from `Item-wise Sales History`. The standard `Item-wise Annual Sales` chart resolves its company through the dynamic filter `frappe.defaults.get_user_default("Company")`; with no default company set, it passed `None` to `get_descendants_of("Company", ...)`.

**Fix:** `infra/erpnext-config/config.yaml` sets `Global Defaults.default_company = Diva Dev` through the idempotent config script. That writes the global default used by the chart's dynamic filter; no standard chart or dashboard document is edited and no ERPNext core file is changed. The fix survives migrate/upgrades because it is stored as a default value.

Verified with a headless browser: `/app/dashboard-view/Selling` loads and renders the charts without the TypeError after the config apply; the standard chart fixture remains untouched. Re-running `make config-dry-run` reports 0 changes.

## 13. Item quick-entry barcode (DEC-78, dev site)

- `infra/erpnext-config` creates the owner-approved `Item.custom_barcode` Data field with `allow_in_quick_entry=1`, placed after `item_name`; it exposes the built-in `standard_rate` as "Selling Price (EGP/Dozen)" and removes `asset_category`/`is_fixed_asset` from quick entry so the quick form stays at seven fields.
- `diva_guard` on Item validate copies the value into the `Item Barcode` child table, sets the barcode UOM to the item stock UOM, clears `custom_barcode`, and rejects a barcode used by another item.
- Verified with `scripts/test_quick_barcode.py`: item saves, barcode appears in the Barcodes table, input is cleared, duplicate is rejected, and the price is written as Dozen 1,200 / Nos 100; a deliberate Dozen edit to 1,250 survives an unrelated Item save; re-saving the Item at 1,320 updates both rows. The Arabic label/description are Translation records. Config re-run 0 changes. A headless browser confirmed the Barcode field in the quick entry.
- Opening quantity: `opening_stock` is visible on the normal Item form and quick entry; `scripts/test_quick_quantity.py` creates an item with 24 Nos, verifies Bin quantity 24 in Stores, valuation 100 from a 1,200/Dozen price, and Dozen/Nos prices 1,200/100.

## 14. Modern print formats with QR (DEC-81, dev site)

- Sales Invoice A4, Purchase Invoice A4, Purchase Receipt A4, Payment Receipt A5 and Journal Entry A4 were redesigned with an RTL modern layout, company name/logo block (monogram when no logo is uploaded), customer-facing fields only and an inline QR verification code.
- `diva_guard.api.qr_svg` renders the QR with PyQRCode (a Frappe dependency) and adds a `viewBox`/crisp edge rendering so it stays decodable when CSS constrains it to 27 mm. No external service.
- Verified print views return 200 with an inline SVG QR for `ACC-SINV-2026-00007`, `ACC-PINV-2026-00006`, `MAT-PRE-2026-00003`, `ACC-PAY-2026-00010` and `ACC-JV-2026-00002`; amount rows use EGP, zero paid/outstanding rows are suppressed, the JE party column is hidden when empty and the JE shows one total.
- QR also renders without an HTTP request through the `jinja.methods` hook (`frappe.get_print` from a worker returned 14,070 bytes with the SVG), so background PDF/email paths are safe. The Arabic party payload (`PAY-26-10-00003`, “المورد”) renders with UTF-8 encoding.
- Pending: upload the real company logo (the block currently falls back to a monogram), and validate the QR/print output on the real 80 mm/A4 printers.

## 15. Party Statement report and print format (ENH-E-01, dev site)

- `apps/custom_reports` installed on `frontend` (`bench list-apps` shows `custom_reports 0.1.0`); the standard report `Party Statement` is synced with module `Custom Reports` (DEC-82) and the Print Format `Party Statement Print` (`print_format_for=Report`, `print_format_type=JS`, `custom_format=1`, standard `No`) is created by `after_migrate`.
- Filters: Company, Party Type (Customer/Supplier), Party (Dynamic Link resolved through `get_options`), From Date (fiscal-year start via `onload`), To Date, Show Cancelled, Letter Head. Verified in a headless browser: `/app/query-report/Party%20Statement` loads with Company `Diva Dev`, Party Type `Customer`, From `2026-07-01`, To `2026-10-29`; the Party selector sets the value and runs the report.
- `scripts/test_party_statement.py` created 2 invoices (1,200 each), 3 partial payments (400 + 300 + 200) and 1 advance (100) for a disposable customer, then checked: invoice 1 paid 700 / outstanding 500, invoice 2 paid 200 / outstanding 1,000, opening 0, invoiced 2,400, paid 1,000, remaining 1,400, advance 100, GL receivable 1,400, mismatch warning absent, and the print-format endpoint returns the format. All checks passed; the script cleans up.
- Supplier path verified with a disposable supplier, one Purchase Invoice 1,200 and one payment 500: opening 0, invoiced 1,200, paid 500, remaining 700, GL payable 700, no warning.
- Print preview (headless Chromium, actual desk): the **Print Statement** button opens Print Settings with `Party Statement Print` and `Portrait` preselected; the preview shows the company header, party block, invoice/payment/advance tables, boxed summary, signatures and the running footer. A4 PDF generated through `frappe.utils.pdf.get_pdf` is one page with `Page 1 of 1`; the footer is extracted as `#footer-html` and repeated. Arabic party data renders RTL via `dir="auto"` (screenshot checked).
- v16.53 has no `Report.default_print_format` column; the JS sets the PDF dialog default and the button preselects the format (DEC-83). No custom field on Report.

## 16. Desk organization and store analytics (ENH-E-02, dev site)

- The Desk **Apps** screen now shows five tiles: ERPNext, **Diva** (`custom_reports`, green bar-chart icon), **Diva Guard** (blue shield icon), **POS Next** (teal terminal icon, tracked patch 0012) and Framework. Verified in a headless browser at `/apps`; the tiles use embedded SVG data-URI logos, so no asset build is needed for the icons.
- Workspaces: `/app/diva-store`, `/app/diva-reports` and `/app/diva-guard`. Each renders its number cards, charts, shortcuts and link cards. Diva Store has six cards (today/month sales, receivables, stock value, active customers, payables) and seven charts (sales trend, item group, warehouse, payment modes, top customers, top suppliers, receivables ageing); Diva Reports has three cards and five charts; Diva Guard has three cards and one chart.
- Amounts use **EGP** (cards and charts); count-only cards/chart show plain numbers. The top customers/suppliers and item-group charts use `number_of_groups` so their legends fit. Ageing charts are custom report charts with `currency=EGP` and use the full width.
- `infra/erpnext-config/desk.yaml` declares the charts, cards and workspaces; `apply_desk.py` created them. Re-running both config scripts reports **0 changes** (`apply.py` 169 no-op, `apply_desk.py` 21 no-op). Unused standard workspaces (Assets, Quality, Projects, Support, Website, CRM, Build, Manufacturing) are hidden through `config.yaml`.
- Verified chart data from the server: sales trend last 12 months, item groups (Consumable/Products/Rest), payment modes (Cash/InstaPay), top customers, top suppliers, sales by warehouse, overrides by status (Pending/Used). Cards: today 481, month 26,041, receivables 2,652, stock value 234,301.40, active customers 10, payables 24,000, pending approvals 47, overrides 56, active rules 12.
- `make lint` clean; `make test` **178 passed, 4 skipped** (5 new planner tests).

## 17. POS Next Escape closes custom popups (ENH-E-03, dev site)

- Added tracked POS Next patch **0013** (`POS/src/composables/useEscapeToClose.js`). Custom full-screen modals register their close callback in opening order; a single document listener closes the topmost one on Escape.
- Covered: POS Settings, Product Management, Promotion Management, Stock Lookup / Warehouse Availability, Invoice Management, Edit Item, Partial Payments. frappe-ui `Dialog` modals (payment, customer, drafts, returns, invoice/shift history, shift opening/closing) already closed on Escape and are unchanged.
- Built the POS frontend with `yarn build` (54 precache entries) and deployed `public/pos` + `www/pos.html` + `www/pos-sw.js` to the dev site.
- Headless Chromium verification on the live POS (`P003 POS`, open shift): Settings, Product Management, Promotions, Stock Lookup, Invoice Management and Edit Item all close on Escape and the POS remains usable; Product Management and Edit Item were checked visually before/after.

## 18. EOD shift report print fixed (ENH-E-04, dev site)

- Root cause: the vendor `POS Next EOD Report` print format read `frappe.db.get_value('POS Profile', doc.pos_profile, 'address')`. `POS Profile` has no `address` field in v16 (it has `company_address`), so `frappe.www.printview.get_html_and_style` failed with `(1054, "Unknown column 'address' in 'SELECT'")`; the POS caught that and showed the generic “EOD report did not print” warning.
- Fix (patch **0014**): use `POS Profile.company_address` and resolve the Address `address_line1`; fall back to no address line when unset. The warning now includes the actual print error (for example, no printer selected) and still offers the Reprint button.
- Verified server-side: `get_html_and_style(doc='POS Closing Shift', name='POSA-CS-26-0000004', print_format='POS Next EOD Report')` returns 5,439 bytes of HTML and 5,017 bytes of style (previously `PrintFormatError`).
- Verified print preview: `GET /printview?doctype=POS Closing Shift&name=POSA-CS-26-0000004&format=POS Next EOD Report&no_letterhead=1` returns **HTTP 200** and contains **END-OF-DAY REPORT**; no `Unknown column` or `Error in print format`.
- `bench --site frontend migrate` synced the corrected print-format JSON into the `POS Next EOD Report` record; rebuilt the POS frontend and deployed the assets. The patch applies cleanly on the post-0013 vendor tree.

## 19. Ops Items and EAN-13 API slice (E-13 partial, dev site)

- `packages/rules-engine` now owns the internal EAN-13 format (GS1 in-store prefix 20–29): `ean13_check_digit`, `format_ean13`, `is_valid_ean13`, `is_internal_ean13`, `generate_ean13`, `next_internal_ean13`; 7 unit tests include the known `2100001000011` / `2100001000028` codes and sequence exhaustion/next-free behaviour.
- `packages/erpnext-adapter` adds item list/search, bulk Item Price and Bin reads, Item Barcode reads, and `add_item_barcode` (preserves existing child rows). Frappe child-table listings return only the row name, so barcode rows are fetched by name.
- `apps/local-api` adds:
  - `GET /api/items?search=&limit=` — item summary with Dozen/Nos prices and stock.
  - `GET /api/items/{item_code}` — item detail with barcodes, batch/serial flags, prices and stock.
  - `POST /api/items/{item_code}/barcodes` — adds a validated EAN-13; generates the next internal code (prefix 20) when the barcode is blank; 409 on duplicate, 422 on invalid.
  - `GET /api/labels?item_code=&uom=&copies=` — label data for the app-drawn dozen/piece label (EAN-13, name, price, copies).
- Verified against the dev site: `GET /api/items?search=DS-85` returned the item with 360/Dozen; detail returned its `9506000140444` barcode; the label endpoint returned Dozen data; a disposable item accepted a generated `2000000000039` Nos barcode and was removed. Local API fake-client suite: 19 endpoint tests.
- Remaining for E-13: the React/TS Ops PWA Items and Labels screens (draw/print EAN-13 labels), product rules/shade variants, then Receive, Transfer, Count and Collect.

## 20. Desk workflows (ENH-E-05, dev site)

**Apps/config**
- New client-only app `diva_desk` (module "Diva Desk", no doctypes) installed with `scripts/install_diva_desk.sh`; `app_include_js = /assets/diva_desk/js/diva_desk.js`, copied into both the backend and frontend benches because each container serves its own `/assets`. `GET /assets/diva_desk/js/diva_desk.js` returns 200.
- `diva_guard` now ships `desk_api.py` (Add New Item, Pay, Desk search, Purchase Receipt automation) and the `Purchase Receipt.on_submit` + `awesomebar_search` hooks.
- `infra/erpnext-config/config.yaml`: `Purchase Receipt.set_warehouse` default **Stores - DD** and label "Accepted Warehouse", `Purchase Receipt Item.warehouse` default **Stores - DD**, `apply_putaway_rule`/`set_posting_time` hidden, `Sales Invoice.set_posting_time` hidden, `Payment Entry.mode_of_payment` default **Cash**, `Item.opening_stock` removed from quick entry (DEC-88). Property setters carry `property_type: Data`; the first apply created two of them with the wrong type, they were deleted and re-applied. Re-run: **0 changes** (`apply.py` 176 no-op/missing).
- Server meta after apply: PR `set_warehouse.default = 'Stores - DD'`, PR Item `warehouse.default = 'Stores - DD'`, PE `mode_of_payment.default = 'Cash'`, PR `apply_putaway_rule.hidden = 1`.

**Server checks — `scripts/test_desk_workflows.py` (all pass)**
- Add New Item: generated `20…` EAN-13 with a valid check digit, Nos stock UOM, Dozen purchase/sales UOM, standard rate = Dozen selling price, barcode child row, Standard Selling prices per Dozen (1,200) and Nos (100), duplicate code rejected.
- Desk search: item by code/name/group/barcode, customer by phone on a linked Contact, supplier by phone on a linked Contact, invoice by id, and the search-bar hook (`frappe.desk.search.awesomebar_search`) returns the invoice.
- Purchase Receipt (1 Dozen of `RD-852`, accepted warehouse Main Inventory - DD, stock UOM Dozen): Purchase Invoice created by ERPNext's mapping and submitted with `update_stock = 0`; Material Transfer submitted with `purchase_receipt_no`, all target warehouses **Stores - DD**, moving the full `stock_qty`; Bin at Stores - DD increased by exactly that quantity; a duplicate run creates no second invoice.
- Sales Invoice: nothing is paid on submit (no Payment Entry GL rows); Pay posts a partial Cash Payment Entry and leaves the rest outstanding; a second Pay clears it and the status becomes **Paid**; over-payment and draft invoices are refused. Amounts are kept as `Decimal` from validation to the Payment Entry fields.
- Review fix verified: the receipt in the test now uses the quick item (stock UOM **Nos**, bought in **Dozen**), so `stock_qty` is 12 and the Material Transfer moves **12 Nos**; the earlier implementation would have moved 1. Idempotency also resumes a draft Purchase Invoice/Stock Entry instead of reporting a false success, and the automation checks create + submit permission on both follow-up doctypes.

**Browser checks — headless Chromium, 2026-10-30 (29 pass)**
- Purchase Receipt: supplier focused, accepted warehouse defaults to Stores - DD, put-away hidden, **Add New Item** opens with code/name/group/barcode/buying/selling Dozen/Nos/quantity/warehouse, Tab moves supplier → warehouse → item row, F1 lists the Diva shortcuts.
- Search bar: Ctrl+K + `RD-852` returns the item with its group.
- Sales Invoice: customer focused; a submitted invoice shows **Print** and **Pay**; the Pay dialog defaults to the full outstanding amount and **Cash**; the Diva A4 preview renders. Screenshots: `/tmp/opencode/desk-verify/*.png`.

**Report print formats — `custom_reports` install hook (DEC-89)**
- One Print Format named after each report (Accounts Receivable, Accounts Payable, General Ledger, Trial Balance, Profit and Loss Statement, Balance Sheet, Stock Balance, Stock Ledger) uses the shared bilingual `diva_report.html`: company header, printed date, filter summary with real labels, zebra table with indentation, currency from the row data (EGP), bold totals, signatures and page footer.
- Rendered through `frappe.query_report.get_print_format_data` + `frappe.render_template` on the live reports: Trial Balance 34 rows, General Ledger 169 rows, Accounts Receivable 6 rows, Stock Balance empty-state (no rows in the period) — all with the Diva layout. Screenshots in `/tmp/opencode/desk-verify/report-*.png`.

## 27. Simplified Item form (E-04 / DEC-99, dev site)

- `apply.py` applied the **34 new Item property setters**; a second run reported **0 changes** (idempotent). Item meta now has **38 hidden fields**: the 34 setters plus four that were already hidden (`attributes`, `customer_code`, `naming_series`, `total_projected_qty`).
- Kept and verified visible: `item_code`, `item_name`, `item_group`, `stock_uom`, `uoms`, `purchase_uom`, `sales_uom`, `standard_rate`, `opening_stock`, `is_stock_item`, `is_sales_item`, `is_purchase_item`, `disabled`, `custom_barcode`, `barcodes`, `image`, `description`, `reorder_levels`, `supplier_items`, `customer_items`, `valuation_rate`, `valuation_method`, `item_defaults`, `has_variants`, `variant_of`, `attributes`, `has_batch_no`, `create_new_batch`, `batch_number_series`, `has_expiry_date`, `shelf_life_in_days`.
- Headless Chromium on a disposable Item: only **Details, Inventory, Accounting, UOM, Purchasing, Sales, Pricing, Connections** tabs render (Manufacturing, Quality and Tax gone); `has_serial_no`, `warranty_period`, `weight_per_unit`, `grant_commission`, `allow_negative_stock`, `end_of_life` are absent; barcodes, batch fields and the reorder table stay; the quick entry still shows its seven fields — **24/24 browser checks pass**.
- `tests/config/test_item_form_simplification.py`: **3 pytest unit tests** (hidden list, the full kept list, batches/variants stay).
