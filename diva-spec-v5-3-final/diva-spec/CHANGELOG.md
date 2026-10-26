# Changelog

All notable changes to the Diva platform. The format follows Keep a Changelog; versions track the specification (`docs/00-index.md`).

## [Unreleased]

### Added
- TASK-P0-04a: `docs/appendix-erpnext-verification.md` records the disposable dev ERPNext 16 stack (erpnext 16.52.1, frappe 16.53.0, mariadb 11.8, redis 6.2, image pinned to `frappe/erpnext:v16.52.1`) and its health evidence.

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
