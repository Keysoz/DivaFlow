# Changelog

All notable changes to the Diva platform. The format follows Keep a Changelog; versions track the specification (`docs/00-index.md`).

## [Unreleased]

### Added
- Phase E start (DEC-71): E-00 recorded (legacy app deleted, nothing to retire) and E-01 baseline from the dev site — `docs/erp-field-register.csv` (28 doctypes, 2,028 rows (2,016 DocField + 12 Custom Field)), app/company/fiscal-year snapshot; provisional until TASK-E-00a.
- P0 closeout: owner confirmed the credential rotation and the n8n webhook check; Arabic glossary/strings reviewed (OPEN-17 closed); POS Next baseline approved (DEC-70); `docs/appendix-p0-exit-gate.md` records the gate status and the remaining owner actions. Post-patch P0-03 smoke re-run passed (`ACC-SINV-2026-00003`, reservation block with `SAL-ORD-2026-00005`).
- E-14b (patch set): `infra/posnext-patches/` with **11** tracked patches on POS Next v2.0.0 — `get_receivable_accounts` cint fix, UOM de-duplication, visible quantity field, `qty*barcode` multiplier, Arabic keys, offline (root-scope worker, fallback, client claim, absolute precache/workbox/manifest), the **owner key map** (F1–F10 and Ctrl shortcuts, F3/F4/F5 open the line editor) and the **combined scan card** (name, code, price per Dozen, stock, qty added). Verified in the browser: 3× scan adds 3 Dozen; Arabic keys render; offline shell loads with the server stopped; shortcuts and the scan card work with a dialog guard. Remaining: hardware receipt/QZ validation and an optional line-note feature.
- TASK-P0-03 (browser checks): automated Playwright pass on the pinned POS Next v2.0.0 — shift opening, barcode scan → UOM dialog → cart (1 → 2 Dozen), Arabic RTL verified visually; offline **fails** at v2.0.0; UOM dialog duplicate "Nos" and a borderless qty input; `get_receivable_accounts` raises `NameError: cint`; POS Profiles require `applicable_for_users`. Recorded in `docs/appendix-posnext-fit-test.md` §1d.
- TASK-P0-01 (partial): `make secret-scan` now also scans the **full git history, all refs** (gitleaks with `safe.directory`, `--redact`); CI checks out the full history. Current result: ~1.16 MB of history, no leaks. Credential rotation and the n8n workflow check remain owner actions.
- TASK-P0-03 (follow-up): POS Next pinned to `v2.0.0` (commit `e0a52c5`; the tag ships code `1.17.0`) and the smoke subset re-run on it: install, POS invoice with Dozen UOM and cash payment, reserved-stock block, uninstall rehearsal; 21 custom fields, no global F-keys, offline service-worker scope gap. Required patches updated; final go/no-go still needs the hardware session.
- ENH-S-02: Bitwarden chosen as the secrets manager (DEC-69); `docs/26-secrets-and-rotation.md` with the secret inventory, quarterly rotation schedule, owner setup and emergency-rotation procedure.
- ENH-S-01: `make audit` and a CI `dependency audit` job — `pip-audit` against the `uv.lock` requirements snapshot; `pnpm audit` runs automatically once a root JavaScript workspace exists (TASK-E-13). Current lockfile: no known vulnerabilities.
- TASK-P0-03: `docs/appendix-posnext-fit-test.md` — POS Next 2.0.0 installed on ERPNext 16.52.1 (develop `47d2c9a`); POS invoice with Dozen UOM, cash payment, shift opening and the reserved-stock block verified; Arabic/RTL and offline/PWA present; required patches identified (`qty*barcode`, full key map, scan info card); provisional go with conditions (pin `v2.0.0`, hardware session, uninstall rehearsal). `docs/14` cells answered and DEC-68 recorded.
- TASK-P0-04a: `docs/appendix-erpnext-verification.md` records the disposable dev ERPNext 16 stack (erpnext 16.52.1, frappe 16.53.0, mariadb 11.8, redis:6.2-alpine, image pinned to `frappe/erpnext:v16.52.1`) and its health evidence.
- TASK-P0-04: verification findings for ERPNext 16: stock reservation is off by default, reserves per Sales Order (partial reservation supported) and natively blocks competing stock movements (RULE-STOCK 5 answered; no backend hold needed for stock), `Item Barcode` carries a UOM and enforces valid EAN-13 plus global uniqueness, the Dozen UOM must be created with whole-number enforcement (native `UOMMustBeIntegerError` for fractions), payment-term templates produce correct schedules, credit limits are enforced at Sales Order submit, `Bin.reserved_qty` must not be used for ATP, and the REST endpoint matrix the adapter needs answers correctly. Verified on the disposable dev stack; the live-site re-check belongs to TASK-E-01.

### Changed
- `docs/12`: OPEN-21 closed (refunds up to the invoice/return total, full or partial, cumulative cap); OPEN-02 closed (PIN held by Administrator, set at TASK-E-14a, stored hashed, never in the repo); DEC-67 records that the repository layout stays nested.

## [0.1.0] - 2026-10-26

### Added
- TASK-P0-10: monorepo foundation: uv workspace (`packages/rules-engine`, `apps/cloud-api`, `apps/local-api`), `make` commands (`setup`, `test`, `lint`, `e2e`, `contract`, `dev-cloud`, `dev-store`, `secret-scan`), CI (ruff, mypy, pytest, gitleaks), Docker Compose for the cloud and store nodes, and placeholder suites with their task IDs.
- TASK-P0-10: `rules_engine.units` Dozen/Nos conversion (1 Dozen = 12 Nos, DEC-20) with exact decimals; floats and booleans are rejected.

### Changed
- `opencode.json`: the `docs` agent model replaced with `opencode-go/mimo-v2.6-flash` (`minimax-m3.1-flash-free` no longer exists in the catalog; docs/21 fallback).
- `docs/12`: OPEN-01 closed (manager maximum discount 15%); OPEN-02 answered (Administrator); OPEN-10 and OPEN-13 deferred with defaults; OPEN-21 partially answered; DEC-02 corrected; DEC-66 recorded (week-1 bake-off skipped).
- `docs/13` and `PROGRESS.md`: TASK-P0-12 skipped — the owner deleted the legacy `diva_store` app.
- `scripts/gen_tasks.py` and `scripts/create_issues.py`: behaviour-preserving lint fixes so `make lint` covers the whole repository.
