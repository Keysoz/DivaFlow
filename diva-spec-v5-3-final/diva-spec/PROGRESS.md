# Progress

The agent updates this file after every task (AGENTS.md section 11, step 9).

| Task | Status | Pull request | Notes |
|---|---|---|---|
| P0-12 | Skipped | — | Legacy `diva_store` app deleted by the owner 2026-10-26; `docs/12` DEC-02 |
| P0-10 | Merged | [#1](https://github.com/Keysoz/DivaFlow/pull/1) | `make lint`/`make test` green locally (86 tests); CI green on the pull request |
| P0-04a | Merged | [#4](https://github.com/Keysoz/DivaFlow/pull/4) | Dev ERPNext 16.52.1 / frappe 16.53.0 on port 8080 recorded; script guards against non-v16 tags |
| P0-04 | Merged | [#6](https://github.com/Keysoz/DivaFlow/pull/6) | ERPNext 16 findings in `docs/appendix-erpnext-verification.md` §2; RULE-STOCK 5 answered (native reservation blocks the counter) |
| P0-03 | Partial — hardware/visual pending | [#8](https://github.com/Keysoz/DivaFlow/pull/8) | pos_next 2.0.0 (tested commit `47d2c9a`) on ERPNext 16: counter flow, Dozen UOM, reserved-stock block PASS; patches needed (`qty*barcode`, key map, scan card); pin `v2.0.0` and re-run the smoke subset |
| ENH-S-01 | Merged | [#9](https://github.com/Keysoz/DivaFlow/pull/9) | `make audit` (pip-audit, clean) + CI dependency job; pnpm audit joins with TASK-E-13 |
| ENH-S-02 | In review (auto-merge) | [#11](https://github.com/Keysoz/DivaFlow/pull/11) | Bitwarden chosen (DEC-69); inventory, rotation schedule and emergency procedure in `docs/26-secrets-and-rotation.md`; owner account setup + P0-01 rotation pending |
