# Progress

The agent updates this file after every task (AGENTS.md section 11, step 9).

| Task | Status | Pull request | Notes |
|---|---|---|---|
| P0-12 | Skipped | — | Legacy `diva_store` app deleted by the owner 2026-10-26; `docs/12` DEC-02 |
| P0-10 | Merged | [#1](https://github.com/Keysoz/DivaFlow/pull/1) | `make lint`/`make test` green locally (86 tests); CI green on the pull request |
| P0-04a | Merged | [#4](https://github.com/Keysoz/DivaFlow/pull/4) | Dev ERPNext 16.52.1 / frappe 16.53.0 on port 8080 recorded; script guards against non-v16 tags |
| P0-04 | Merged | [#6](https://github.com/Keysoz/DivaFlow/pull/6) | ERPNext 16 findings in `docs/appendix-erpnext-verification.md` §2; RULE-STOCK 5 answered (native reservation blocks the counter) |
| P0-03 | Complete — hardware validation deferred to purchase (owner) | [#8](https://github.com/Keysoz/DivaFlow/pull/8) | Pinned `v2.0.0` + 12 patches; browser checks, post-patch smoke (`ACC-SINV-2026-00003`), key map and scan card verified; remaining: receipt/QZ validation when the hardware arrives |
| E-14b | Partial — 12 patches; offline, key map and scan card verified | — | `infra/posnext-patches/` on tag `v2.0.0`; remaining: hardware receipt/QZ validation |
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
