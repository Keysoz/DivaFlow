# Progress

The agent updates this file after every task (AGENTS.md section 11, step 9).

| Task | Status | Pull request | Notes |
|---|---|---|---|
| P0-12 | Skipped | — | Legacy `diva_store` app deleted by the owner 2026-10-26; `docs/12` DEC-02 |
| P0-10 | Merged | [#1](https://github.com/Keysoz/DivaFlow/pull/1) | `make lint`/`make test` green locally (86 tests); CI green on the pull request |
| P0-04a | Merged | [#4](https://github.com/Keysoz/DivaFlow/pull/4) | Dev ERPNext 16.52.1 / frappe 16.53.0 on port 8080 recorded; script guards against non-v16 tags |
| P0-04 | Merged | [#6](https://github.com/Keysoz/DivaFlow/pull/6) | ERPNext 16 findings in `docs/appendix-erpnext-verification.md` §2; RULE-STOCK 5 answered (native reservation blocks the counter) |
| P0-03 | Partial — hardware/visual pending | [#8](https://github.com/Keysoz/DivaFlow/pull/8) | Pinned `v2.0.0` (code 1.17.0) and re-ran the smoke subset: install, Dozen UOM invoice, reserved-stock block, uninstall rehearsal PASS; 21 fields, no F-keys, SW scope gap; patches + hardware session remain |
| ENH-S-01 | Merged | [#9](https://github.com/Keysoz/DivaFlow/pull/9) | `make audit` (pip-audit, clean) + CI dependency job; pnpm audit joins with TASK-E-13 |
| ENH-S-02 | Merged | [#11](https://github.com/Keysoz/DivaFlow/pull/11) | Bitwarden chosen (DEC-69); inventory, rotation schedule and emergency procedure in `docs/26-secrets-and-rotation.md`; owner account setup + P0-01 rotation pending |
| P0-09 | Partial — same-host restore proven; datasets + separate VM pending | [#13](https://github.com/Keysoz/DivaFlow/pull/13) | Backup 1.2 MB restored into a second site; row counts match (items, customers, invoices, custom fields); `docs/appendix-backup-restore.md` |
