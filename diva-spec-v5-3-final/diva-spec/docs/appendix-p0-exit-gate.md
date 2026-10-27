# Appendix: P0 exit gate status

Status as of 2026-10-27. Gate definition: `docs/09-build-plan.md` (Phase P0 exit gate) with the additions from `docs/16` (ENH-R-01, R-03, R-04, S-01, S-02).

## 1. Gate items

| Gate item | Status | Evidence / owner action |
|---|---|---|
| No exposed secrets | **Done** — the owner rotated the exposed credentials (2026-10-27) | `make secret-scan` clean on the working tree **and** the full git history (all refs, ~1.2 MB); no secrets in workflows; Bitwarden adopted (`26-secrets-and-rotation.md`) |
| P0-02 legacy webhooks | **Done** — owner checked the n8n instance | Owner confirmation 2026-10-27 |
| P0-03 results recorded | **Done — hardware validation deferred to purchase** | `appendix-posnext-fit-test.md`; post-patch smoke: `ACC-SINV-2026-00003` (1 Dozen, EGP 1,440, paid), reservation block with `SAL-ORD-2026-00005`; 10-patch set verified |
| P0-04 results recorded | **Done** | `appendix-erpnext-verification.md` §2 |
| CI green | **Done** | three jobs (lint/types/tests, dependency audit, secret scan) on `main` |
| Applications submitted | **Pending — owner** | P0-11: TikTok developer app + audit; Meta app permissions for FB/IG publishing |
| ENH-R-01 onboarding package | **Partially ready** | repo, CI, secrets manager done; pending: hardware (purchase), datasets, applications |
| ENH-R-03 / ENH-R-04 | **Done** | PR template + task template in `AGENTS.md` / `.github` |
| ENH-S-01 supply-chain scanning | **Done** | `make audit` + CI job |
| ENH-S-02 secrets manager | **Done** | Bitwarden chosen (DEC-69), runbook `26`; owner confirmed the vault and the initial rotation (2026-10-27) |

## 2. Remaining P0 tasks (owner)

| Task | What the owner does |
|---|---|
| P0-05 infrastructure | Record: store VM size (vCPU/RAM/disk), internet uptime and latency to the chosen cloud region, WireGuard feasibility, UPS model; choose the cloud provider |
| P0-06 hardware | Buy the USB scanner, 80 mm thermal receipt printer and label printer; record the models. **Deferred by the owner (pay later)** |
| P0-07 WhatsApp / Meta | Status of the WhatsApp provider, approved templates and number; Chatwoot compatibility; Meta business verification; Instagram/Facebook Page connection |
| P0-08 accountant | **Answered (owner, 2026-10-27)**: the six modes are Cash, Bank Transfer, Vodafone Cash, InstaPay, ECash and WePay; one ledger account per mode, mapped in TASK-E-09. VAT/e-invoicing are closed (none, DEC-26) |
| P0-09 datasets + VM | Provide a second VM for the restore proof; the item master export; 100 anonymized chats; 50 voice notes (anonymize locally — never send real customer data to any model, docs/21 §4) |
| P0-11 applications | Submit the TikTok developer app + audit; request Meta app permissions for publishing |
| Merge PR #13 | The backup/restore rehearsal PR is `critical`, checks green — the owner merges it |

When the hardware arrives, the deferred P0-03/P0-06 validation runs: Arabic 80 mm receipt, QZ Tray, Arabic keyboard layout, full offline shift, performance figures, returns and shift closing end-to-end.

## 3. What "done" means for the agent side

Everything the agent can do without owner accounts, hardware or a second VM is complete: repo and CI, dev ERPNext verification, POS Next fit test and patch set, secrets scanning, dependency audit, backup/restore rehearsal, decision records and progress. The gate itself stays open until the owner items above are finished.
