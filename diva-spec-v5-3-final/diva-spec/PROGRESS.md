# Progress

The agent updates this file after every task (AGENTS.md section 11, step 9).

| Task | Status | Pull request | Notes |
|---|---|---|---|
| P0-12 | Skipped | — | Legacy `diva_store` app deleted by the owner 2026-10-26; `docs/12` DEC-02 |
| E-00 | Done — nothing to retire | — | The legacy app is deleted; no salvage or cutover remains (DEC-02/DEC-71) |
| E-01 | Done (provisional on dev) | — | `docs/erp-field-register.csv` (28 doctypes, 2,028 rows) + apps/company/FY snapshot; regenerate at TASK-E-00a |
| E-02 | Done (dev) | — | Manufacturing workspace hidden via the config script; HR/Payroll absent; per-role refinement at E-16 |
| E-03 | Done (dev) | — | Idempotent `infra/erpnext-config/apply.py` + config + tests; re-run prints 0 changes; tax fields hidden (DEC-26) |
| E-04 | Partial (dev) | — | Dozen whole-number, negative stock off, reservations on, item groups Accessories/Cosmetics via config; batch/expiry per item + simplified Item form pending |
| E-05 | Partial (dev) | — | `Wholesale` tier price list created; per-tier prices and price-edit permissions later (E-16) |
| E-12 | Partial — rules + adapter + local-api skeleton | — | rules-engine MOQ/discount/min-order with tests; typed adapter with contract tests (pass on the dev site); local-api `/health`, item-by-barcode, counter rules with bearer auth. More endpoints and nightly staging later |
| E-06 | Done (dev) | — | 12 items with Dozen + Nos EAN-13 barcodes and per-Dozen prices; uniqueness enforced (P0-04) |
| E-07 | Partial (dev) | — | DEC-49 warehouses + opening stock (Stock Reconciliation 120 Nos each); FIFO valuation audit pending |
| E-08 | Partial (dev) | — | Suppliers + Purchase Invoice with Update Stock verified (one stock movement per delivery); supplier payments/payables and the China flow remain |
| E-09 | Partial (dev) | — | Customers, six modes + accounts, paid POS invoice and a credit invoice with outstanding balance; receivable report reconciliation remains |
| E-15 | Partial (dev) | — | Bilingual A4 invoice, 80 mm receipt and payment receipt as data-driven Jinja print formats (`infra/erpnext-config/print_formats/`, applied idempotently); EGP symbol set; browser render verified. Pending: statements, saved-filter reports, locally bundled Arabic font and the real 80 mm printer test (hardware deferred) |
| E-10 | Partial (dev) | — | Five expense categories + synthetic cash/bank expenses via Journal Entry (`scripts/seed_dev_expenses.py`); daily cash closing checklist and ledger reconciliation pass (cash opening 8,140 + receipts 1,624 − expenses 1,490.50 = 8,273.50). Pending: receipt attachments UI and the Ops expenses screen |
| E-16 | Done (dev, baseline) | — | `scripts/seed_dev_users.py`: manager + cashier accounts and permission checks pass. POS Next `Custom DocPerm` rows shadow ERPNext defaults (DEC-72); `infra/erpnext-config` mirrors the standard rows back (idempotent). Vendor `POSNext Cashier` granted to the cashier; void approval still to be enforced in local-api |
| P0-10 | Merged | [#1](https://github.com/Keysoz/DivaFlow/pull/1) | `make lint`/`make test` green locally (86 tests); CI green on the pull request |
| P0-04a | Merged | [#4](https://github.com/Keysoz/DivaFlow/pull/4) | Dev ERPNext 16.52.1 / frappe 16.53.0 on port 8080 recorded; script guards against non-v16 tags |
| P0-04 | Merged | [#6](https://github.com/Keysoz/DivaFlow/pull/6) | ERPNext 16 findings in `docs/appendix-erpnext-verification.md` §2; RULE-STOCK 5 answered (native reservation blocks the counter) |
| P0-03 | Complete — hardware validation deferred to purchase (owner) | [#8](https://github.com/Keysoz/DivaFlow/pull/8) | Pinned `v2.0.0` + 11 patches; browser checks, post-patch smoke (`ACC-SINV-2026-00003`), key map and scan card verified; remaining: receipt/QZ validation when the hardware arrives |
| E-14b | Partial — 11 patches; offline, key map and scan card verified | — | `infra/posnext-patches/` on tag `v2.0.0`; remaining: hardware receipt/QZ validation and an optional line-note feature |
| ENH-S-01 | Merged | [#9](https://github.com/Keysoz/DivaFlow/pull/9) | `make audit` (pip-audit, clean) + CI dependency job; pnpm audit joins with TASK-E-13 |
| ENH-S-02 | Done | [#11](https://github.com/Keysoz/DivaFlow/pull/11) | Bitwarden chosen (DEC-69); inventory, rotation schedule and emergency procedure in `docs/26-secrets-and-rotation.md`; owner confirmed the vault and the rotation 2026-10-27 |
| P0-01 | Done — owner rotated the credentials | [#14](https://github.com/Keysoz/DivaFlow/pull/14) | `make secret-scan` clean on the working tree **and** the full history (all refs, ~1.16 MB); rotation confirmed by the owner 2026-10-27 |
| P0-02 | Done — owner checked the n8n instance | — | Owner confirmation 2026-10-27 |
| P0-05 | Pending — owner | — | Store VM, internet, WireGuard, UPS numbers; cloud provider choice |
| P0-06 | Deferred — owner buys the hardware later | — | USB scanner, 80 mm receipt printer, label printer; models to record |
| P0-07 | Pending — owner | — | WhatsApp provider/templates/number, Chatwoot compatibility, Meta verification, IG/FB pages |
| P0-08 | Done — modes confirmed | — | Cash, Bank Transfer, Vodafone Cash, InstaPay, ECash, WePay; one account per mode, mapping in TASK-E-09; VAT/e-invoicing closed (none) |
| P0-11 | Pending — owner | — | TikTok developer app + audit; Meta publishing permissions |
| P0-09 | Partial — rehearsal done; PR #13 open (critical) | [#13](https://github.com/Keysoz/DivaFlow/pull/13) | Same-host restore verified (row counts match); separate-VM proof + datasets pending owner |
| ENH-R-01 | Partial — onboarding package | — | Repo, CI, secrets manager done; pending hardware, datasets, applications |
