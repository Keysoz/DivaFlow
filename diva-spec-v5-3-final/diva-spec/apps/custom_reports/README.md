# custom_reports

Diva custom Frappe reports for ERPNext v16. The first report is **Party
Statement** (`كشف حساب`): a printable statement of account for one Customer or
one Supplier.

The report lives in this app, not in ERPNext. `Report.module` decides which app
Python is imported from: with `module = "Accounts"` Frappe would look for
`erpnext.accounts.report.party_statement.party_statement`, i.e. code inside
ERPNext core. This app therefore declares the module **Custom Reports**
(DEC-82). The report still appears in the desk like any standard report.

## What is included

```
apps/custom_reports/
├── pyproject.toml
├── README.md
└── custom_reports/
    ├── __init__.py
    ├── hooks.py                     after_install / after_migrate
    ├── install.py                   creates/updates the report print format
    ├── modules.txt                  "Custom Reports"
    ├── public/js/custom_reports.bundle.js
    ├── print_format/
    │   └── party_statement_print.html   Jinja/JS report print format
    └── custom_reports/
        ├── __init__.py
        └── report/party_statement/
            ├── __init__.py
            ├── party_statement.json      Report definition
            ├── party_statement.py        data logic (Script Report)
            └── party_statement.js        filters and the Print Statement button
```

There is also a reproducible installer for the disposable dev stack and an
integration test at the repository root:

- `scripts/install_custom_reports.sh`
- `scripts/test_party_statement.py`

## Install on a v16 bench

The app is part of the Diva monorepo, so copy (or symlink) the folder into the
bench and register it in the virtualenv and `sites/apps.txt`. Run from the Diva
repository root unless stated otherwise.

```bash
# 1. copy the app into the bench
cp -R apps/custom_reports /path/to/frappe-bench/apps/custom_reports

# 2. register the Python package and the app
cd /path/to/frappe-bench
./env/bin/pip install -e apps/custom_reports
grep -qx custom_reports sites/apps.txt || printf '\ncustom_reports\n' >> sites/apps.txt

# 3. install and migrate (after_migrate creates/updates the print format)
bench --site YOUR_SITE install-app custom_reports
bench --site YOUR_SITE migrate

# 4. build assets (only needed if you change the public bundle)
bench build --app custom_reports

# 5. clear the cache and restart the workers
bench --site YOUR_SITE clear-cache
bench restart
```

On a development Docker stack with the app copied into
`/home/frappe/frappe-bench/apps/custom_reports`, the repository script does the
same steps and restarts the backend container:

```bash
./scripts/install_custom_reports.sh
```

To upgrade after pulling a change: repeat steps 1 and 3–5. `after_migrate`
updates the print format only when its HTML changed.

## Open the report

Desk → **Custom Reports → Party Statement** (or
`/app/query-report/Party%20Statement`).

Filters:

| Filter | Default | Notes |
|---|---|---|
| Company | user default company | required |
| Party Type | Customer | Customer or Supplier |
| Party | — | Dynamic Link filtered by Party Type |
| From Date | start of the company's fiscal year | filled by the report's `onload` |
| To Date | today | |
| Show Cancelled | off | cancelled rows are shown but never counted |
| Letter Head | — | optional; its header replaces the built-in company header |

The screen shows the opening balance, invoices, credit/debit notes, payments,
advances and four summary cards. A red warning appears only if the statement
closing balance differs from the GL balance; the warning is never printed.

## Print

Click **Print Statement** (the report adds this button). It opens the standard
print dialog with:

- Print Format `Party Statement Print` already selected
- Orientation `Portrait`

Press **Submit** to open the browser print preview; the PDF keeps the same
layout. The format is A4 portrait with:

- company header (logo when the Company has one) or the selected Letter Head
- party block with name, ID, address, phone, e-mail and tax ID (`dir="auto"`)
- invoices, credit/debit notes, payments and advances, each with its own table
  and a bold total row
- a boxed, right-aligned summary with the remaining balance highlighted
- three signature lines and a running footer with company contact details and
  `Page X of Y`

**Default print format in v16.** Frappe 16.53 has no `Report.default_print_format`
database field (the key that older ERPNext report JSON files carry is ignored).
The app therefore:

1. sets `report_doc.default_print_format` in `party_statement.js` so the built-in
   **PDF** dialog preselects `Party Statement Print`, and
2. adds the **Print Statement** button so the normal print dialog also starts
   with the format and portrait orientation preselected.

There is no custom field on Report and no core edit (DEC-83). If the built-in
**Print** action is used instead, choose `Party Statement Print` in its Print
Format field; the browser remembers nothing between reports in v16. The built-in
**PDF** action preselects the format but opens with Landscape selected — choose
Portrait, or use **Print Statement**.

The report's `ref_doctype` is `Sales Invoice`, so Frappe checks print
permission against Sales Invoice for both party types (a Report can reference
only one doctype). Accounts Manager/User roles normally have both Sales and
Purchase Invoice print permission.

## Tests

`scripts/test_party_statement.py` creates a disposable customer, two invoices,
three partial payments and one advance, then checks:

- invoice paid/outstanding per invoice (700/500 and 200/1000)
- summary opening 0, invoiced 2,400, paid 1,000, remaining 1,400
- the advance is listed with 100 unallocated
- the closing balance equals the GL receivable balance
- no mismatch warning is raised
- `frappe.desk.query_report.get_print_format_data` returns the report format

Run it against the dev site:

```bash
ERPNEXT_URL=http://localhost:8080 \
ERPNEXT_USER=Administrator ERPNEXT_PASSWORD=admin \
python3 scripts/test_party_statement.py
```

Set `KEEP_DATA=1` to keep the generated documents for a visual print check. The
script removes what it created by default. The supplier path (Purchase Invoice,
Payable, supplier payment) was verified with the same totals on the dev site.

## Design notes

- Only submitted documents are included unless **Show Cancelled** is on;
  cancelled rows never add to the totals.
- Opening and closing balances come from `GL Entry` (Receivable/Payable, party
  filter, `is_cancelled = 0`).
- Invoices show `paid_amount` (which includes Payment Entry allocations and any
  amount paid on the invoice itself, e.g. a POS sale). The part not covered by
  Payment Entry references is counted as **paid at counter** in the summary.
- Refunds are Payment Entries in the opposite direction (a customer refund is a
  `Pay` entry). They are included with a negative amount so the statement agrees
  with the ledger.
- Row amounts use the document currency; totals and the GL comparison use the
  company currency, with an on-screen note when they differ.
- Every query is `frappe.get_all` with parameterised filters. User permissions
  and user-permission conditions apply automatically.
- The report print format is a client-side Frappe template (`print_format_for =
  Report`, `print_format_type = JS`), so it uses `__()` for labels and
  `frappe.render_template`; it never calls the server or an external service.
