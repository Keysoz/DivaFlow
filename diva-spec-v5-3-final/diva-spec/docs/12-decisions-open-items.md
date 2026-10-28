# 12 Decisions, Open Items, Assumptions, Risks

## 1. Decision log (in force)
| ID | Decision |
|---|---|
| DEC-01 | One master specification: a repository of Markdown files plus a single-file edition |
| DEC-02 | **Corrected 2026-10-26:** the owner deleted the legacy `diva_store` app. `TASK-P0-12` is skipped and `E-00` collapses to confirming nothing depends on the deleted app (earlier answers: none, then exists and in daily use) |
| DEC-03 | Build order: P0, then ERPNext (E), then Publishing (PUB), then chat orders (O), Bosta (B), chat hub (C), AI (A), Mini App (M), growth (G) |
| DEC-04 | No custom fields. No custom code inside ERPNext except the two governed exceptions in DEC-29. Configuration stored as data is allowed through the idempotent config script |
| DEC-05 | Split deployment: cloud node for chat, AI, publishing, dashboard; store node for ERPNext, POS and Ops |
| DEC-06 | When the store link is down, pause new chat orders and tell customers |
| DEC-07 | MOQ applies at the counter and in chat; the 3,000 EGP minimum applies to chat orders only |
| DEC-08 | Chat reservations are protected from counter sales |
| DEC-09 | One ERPNext user and API credential per staff member, held encrypted by local-api |
| DEC-10 | Public posts show no wholesale prices |
| DEC-11 | Cashier UI Arabic with English switch |
| DEC-12 | Shipping fee decided per order by staff; the AI never quotes it |
| DEC-13 | Cashier discount up to 5%; above needs manager PIN |
| DEC-14 | No credit and no partial payment at the counter; credit only in manager back-office invoices |
| DEC-15 | Messaging channels at launch: WhatsApp, Instagram, Facebook Messenger. TikTok DM later |
| DEC-16 | WhatsApp is already on the Business API; provider and Chatwoot compatibility checked in P0-07 |
| DEC-17 | AI rollout: offline evaluation, shadow, staff-assisted, limited auto, expansion |
| DEC-18 | Publish gate: barcode, price, MOQ, pack size, images and stock fields required |
| DEC-19 | Counter POS: test first. Superseded by DEC-29 |
| DEC-20 | Units: stock in Nos (pieces); buying, selling and prices in Dozen (1 = 12) |
| DEC-21 | WhatsApp publishing: both opt-in broadcast templates and a manual ready-to-post pack |
| DEC-22 | Specification is agent-neutral (AGENTS.md); agent not yet chosen |
| DEC-23 | No fixed dates; staged releases at exit gates |
| DEC-24 | Categories: women's accessories and jewelry; makeup and cosmetics. HR, payroll and manufacturing hidden |
| DEC-25 | Planning volumes: 30–100 chats and 20–60 counter invoices per day |
| DEC-26 | No VAT and no e-invoicing for this shop; tax fields hidden |
| DEC-27 | Hardware owned: USB scanner, thermal receipt printer, label printer (models to record) |
| DEC-28 | Labels are drawn by Diva Ops, not ERPNext print formats |
| DEC-29 | **Counter POS is POSNext**, configured, plus the minimal `diva_guard` app for server-side rules and a small tracked POSNext patch set. Fallback: build a POS mode in Diva Ops if the fit test fails |
| DEC-30 | Rules are enforced on the server at invoice validate and submit (`diva_guard`), never only in the UI. `Diva Product Rule` doctype in ERPNext is the master of MOQ, step and publish flags |
| DEC-31 | Purchase flow: goods and supplier invoices arrive together, so Purchase Invoice with Update Stock |
| DEC-32 | Barcodes and new item codes are internal EAN-13 (GS1 in-store prefix); existing barcodes and item codes are kept |
| DEC-33 | WhatsApp broadcast budget cap is not required for now (optional setting, off by default) |
| DEC-34 | Final ERPNext stack and per-feature choices are in `14`: standard ERPNext (configured), BrainWise POS Next for the counter with `diva_guard` and a small patch set, Diva Ops for Receive, Transfer, Count, Labels, Items, Collect and Pack, Control Room for management; legacy app retired |
| DEC-36 | Counter look and feel is a requirement: scan info card and the owner's current key map, implemented as POS Next patches; if impossible, build the POS mode in Diva Ops |
| DEC-37 | Enhancement backlog decided by the planner at the owner's request: all P0 and 30 selected P1 items accepted (53 items, about 556 h); the rest deferred (`16`) |
| DEC-38 | The coding agent works on dev and staging only and never holds production administrator credentials; production deploys through CI approved by the owner after a backup |
| DEC-39 | Arabic and English everywhere; Arabic is primary with RTL; per-user language; resellers detected per conversation (`19`) |
| DEC-40 | Western digits (0–9) by default with an optional Arabic-Indic setting; input accepts both; Gregorian dates; week starts Saturday; amounts as ج.م or EGP |
| DEC-41 | `item_name` is Arabic; English name and bilingual descriptions live in `Diva Product Rule` (no custom fields on Item) |
| DEC-42 | Arabic receipts and labels render as raster images if the printer cannot shape Arabic natively |
| DEC-43 | **Specification v4.0 is final.** Open items keep their defaults and change only through decision records |
| DEC-44 | Deposit rule: **new resellers pay a 30% deposit** of the goods subtotal after discounts (excluding shipping and taxes); stock is reserved only after a reviewer verifies it; trusted resellers follow their policy (COD after 3 completed orders reserves at confirmation); deposit is a customer advance; deadline default 24 h |
| DEC-45 | Inventory valuation is FIFO, enabled only after a staging audit of existing valuation and stock ledger |
| DEC-46 | At ready-for-dispatch the Delivery Note and then the Sales Invoice are created, with the deposit advance allocated |
| DEC-47 (amended by DEC-75 for China currency/advances) | Two purchasing flows: local (Purchase Invoice with Update Stock) and China import (Purchase Order, Purchase Receipts, Landed Cost Voucher, foreign currency, advances, bank only) |
| DEC-48 | Payment modes: Cash, Bank Transfer, Vodafone Cash, InstaPay, ECash, WePay; China suppliers bank only (guard rule) |
| DEC-49 | Warehouses: Main Inventory, Shop (counter), Gallery, Returns and Defects, In Transit |
| DEC-50 | Discount limit applies to the effective discount against the price list, enforced on the server |
| DEC-51 | Price conflicts resolve customer-specific, then group list, then channel default; unresolved ties need manager review; the price source is logged |
| DEC-52 | Employee returns within limits: valid reference, eligible quantity, reason; manager approval above the cash-refund limit or without a reference; stock to Returns and Defects until assessed |
| DEC-53 | Manual couriers supported beside Bosta (courier, tracking, fee, status, outcome); preferred courier on the reseller profile |
| DEC-54 | Reconfirmed 2026-10-20: stock in pieces with Dozen = 12; no VAT and no e-invoices. Not adopted: Telegram-first ordering, a website storefront (deferred to growth), keeping the old `diva_store` app, putting the integration layer inside it |
| DEC-55 | AI coding tools budget is $20 to $60 per month with spending caps; starting setup and lanes in `21` |
| DEC-56 | Chinese models only through OpenCode Go (no training, 0-day retention per its privacy table, re-checked monthly), another zero-retention host, or self-hosted; only code and anonymized test data go to any model; payment, deposit, login and `diva_guard` code also get a Western-vendor review |
| DEC-57 | Harness is OpenCode with OpenCode Go (flat subscription). Role mapping in `21` section 7 and `opencode.json`: GLM-5.2 plans and reviews DeepSeek's code; DeepSeek V4 Pro implements and reviews GLM's code; DeepSeek V4 Flash for bulk; Kimi for front-end; a free model for documentation; a Western-vendor model reviews all critical code |
| DEC-58 | Invoices, receipts and statements can be sent to customers and suppliers on WhatsApp besides printing: level 1 free (Print, Download PDF, Open in WhatsApp) in Phase E, level 2 one-click API send with utility templates in Phase PUB (`22`) |
| DEC-59 | One-click broadcast with a cost preview and confirmation; free channels first (Telegram, WhatsApp Channel pack); WhatsApp marketing templates only to opted-in contacts; WhatsApp is not the cheapest option, about $0.0644 per message in Egypt |
| DEC-60 | The model for each job is assigned in `opencode.json` and `21` section 7, based on Go's per-model monthly limits: volume work on high-quota models, strong low-quota models for planning, hard problems and reviews; Go ($10) for Phase 0, Go Plus ($40) from Phase E; superseding the DEC-57 mapping |
| DEC-61 | **Specification v5.0 is final and build-ready**; start with Phase P0 using `tasks.csv` and `docs/20-start-here.md` |
| DEC-62 | Autopilot: the agent runs inside a dedicated Linux dev VM with broad permissions but no production credentials; one task at a time with `scripts/run-task.sh`; non-critical pull requests auto-merge when CI passes; critical ones wait for the owner (`24`) |
| DEC-63 | No ERPNext exists yet: a disposable dev ERPNext 16 is installed with frappe_docker for development and tests (`P0-04a`); the production ERPNext is installed on the store VM in `E-00a` |
| DEC-64 | Cost savings adopted (`25`): small cloud server first; customers message first with the cheapest valid WhatsApp send path and phone verification by inbound message; routine questions answered by fixed logic before any model; small model first with escalation and caching; self-hosted Uptime Kuma and GlitchTip; media and backups on Cloudflare R2 or Backblaze B2 |
| DEC-65 | Not adopted: dropping n8n (it stays for schedules and briefs) and replacing AI-generated backgrounds (they stay, always on top of the real product photo) |
| DEC-35 | POS Next is pinned and never auto-upgraded; every upgrade and an uninstall are rehearsed on staging; the unrelated older "POSNext" by exvas is never installed |
| DEC-66 | Week-1 model bake-off (`21` section 5) skipped by the owner on 2026-10-26; the current OpenCode setup (DEC-60) is kept |
| DEC-67 | Repository layout stays nested: the project lives at `diva-spec-v5-3-final/diva-spec/` inside the `Keysoz/DivaFlow` repository, and CI runs from the repository root with `working-directory`. Restructure only if the owner asks (owner, 2026-10-26) |
| DEC-69 | Secrets manager is **Bitwarden** (Secrets Manager for machine secrets, organization vault for people, 2FA, collections per environment); rotation schedule and emergency procedure in `26-secrets-and-rotation.md` (owner, 2026-10-27) |
| DEC-70 | **POS Next baseline approved** (owner, 2026-10-27): pin tag `v2.0.0` (vendor code `1.17.0`) plus the tracked patch set in `infra/posnext-patches/`; hardware validation is deferred until the owner buys the scanner and printers. The modified source stays available (AGPL) |
| DEC-71 | **Phase E starts on the dev stack before the full P0 gate** (owner, 2026-10-27): the remaining P0 owner items (applications, store VM, datasets, hardware) do not block configuration and adapter work on the disposable dev site. TASK-E-00a (production install) and cutover still require the owner and the gate |
| DEC-75 | **China imports are accounted in EGP** (owner, 2026-10-28): the Chinese supplier is registered like an Egyptian supplier; items and prices are in EGP, with no foreign currency, exchange rate or exchange-difference handling. The flow keeps Purchase Order, partial Purchase Receipts, a Landed Cost Voucher for freight/customs, a Purchase Invoice and two instalments (40% then 60%), paid by bank transfer |
| DEC-74 | **Cloud auth baseline** (agent, 2026-10-28): owner bootstrap is a one-time token-guarded call; passwords use Argon2id; access tokens are 30-minute JWTs and refresh tokens rotate and are stored hashed; MFA (TOTP plus hashed single-use recovery codes) is mandatory for the owner and optional for staff; TOTP secrets use a dedicated `MFA_ENCRYPTION_KEY`; refresh rotation is atomic and reuse revokes the session family; exactly one owner is enforced; every sensitive action is written to an audit log. Secrets stay in the secret manager; `ENVIRONMENT=production` refuses the dev JWT/bootstrap defaults |
| DEC-73 | **diva_guard enforcement and PIN approvals** (agent, 2026-10-28): rules are enforced in Sales Invoice `validate` for every client, not in the browser; non-managers cannot create unpaid/partial invoices even without `is_pos`; the manager PIN is a PBKDF2-HMAC-SHA256 hash in `Diva Guard Settings` (PIN from the secret store), and approvals are 10-minute single-use tokens sent as `X-Diva-Override-Token`; every approval is audited in `Diva Override Approval`. POS Next must add the PIN dialog/header in E-14b/E-14d. Critical code: owner-approved merge and a Western-vendor review |
| DEC-72 | **POS Next custom permissions are mirrored back** (agent, 2026-10-28): POS Next ships `Custom DocPerm` rows for 15 doctypes (Sales Invoice, Journal Entry, Payment Entry, Customer, Item, Warehouse, Bin, Account, POS Profile/Opening/Closing, Territory, Address, Promotional Scheme, Serial and Batch Bundle). Frappe ignores the standard `DocPerm` table once custom rows exist, so after installing POS Next every role without a vendor row lost access — including `Accounts User` on Sales Invoice and Journal Entry. `infra/erpnext-config` now mirrors the ERPNext standard rows into `Custom DocPerm` (idempotent; POS Next-only roles are never touched and standard-role rows are repaired to the ERPNext baseline) and the cashier also gets the vendor `POSNext Cashier` role required by POS Next. Re-run the config after every POS Next install or upgrade. The POSNext Cashier role includes cancel on Sales Invoice for POS void; the local-api rules engine still governs voids and manager approval (TASK-E-14a) |
| DEC-68 | POS Next fit test (TASK-P0-03): **provisional go** on ERPNext 16. Pin executed: **`v2.0.0`** (commit `e0a52c5`; the tag ships code `1.17.0`); smoke subset passed (POS invoice with Dozen UOM, reserved-stock block, uninstall rehearsal; 21 fields, no global F-keys). Automated browser checks (2026-10-27): RTL verified visually; **offline fails at v2.0.0**; scan flow works but the UOM dialog duplicates "Nos" and the qty input is borderless (easy to miss); `get_receivable_accounts` raises `NameError: cint`; a POS Profile needs `applicable_for_users`. Patch set applied on v2.0.0 (`infra/posnext-patches/`, 11 patches): `get_receivable_accounts` cint fix, UOM de-duplication, visible quantity field, `qty*barcode`, two Arabic keys, and the offline fixes (scope, fallback, client claim, absolute precache + workbox import + injected manifest entry) — offline **verified** with the server stopped (shell + assets load; full offline selling to confirm). The smoke subset was re-run on the patched build (appendix §1f); the key map and the combined scan card were added and verified (patch 11, §1g; F5 opens the line editor because the vendor has no note field). Remaining: hardware receipt/QZ validation (owner buys the hardware later, 2026-10-27); the baseline is approved (DEC-70). `diva_guard` stays mandatory; EGP currency check. The owner authorised the dev site with synthetic data and deferred the hardware (2026-10-26). Final go/no-go after the hardware session (`appendix-posnext-fit-test.md`) |

## 2. Open owner questions (the agent must ask, not guess)
| ID | Question | Default until answered |
|---|---|---|
| OPEN-01 | ~~Manager maximum discount~~ Closed: 15% (owner, 2026-10-26) | closed |
| OPEN-02 | ~~Who holds approval PINs and how are they set~~ Closed: Administrator holds the approval PIN; the owner sets and rotates it at TASK-E-14a, stored as a salted hash in `diva_guard` settings, never in the repo (owner, 2026-10-26) | closed |
| OPEN-03 | Reseller tier definitions and price lists | Standard plus one tier |
| OPEN-04 | Return policy for opened cosmetics | No returns of opened cosmetics unless defective |
| OPEN-05 | ~~Purchase flow~~ Closed: Purchase Invoice with Update Stock (DEC-31) | closed |
| OPEN-06 | Near-expiry threshold | 90 days |
| OPEN-07 | WhatsApp provider and Chatwoot compatibility | Resolved in P0-07 |
| OPEN-08 | ~~VAT and e-invoicing~~ Closed: none (DEC-26) | closed |
| OPEN-09 | Hardware models | Record in P0-06 |
| OPEN-10 | ~~Which ledger account each mode posts to~~ Closed: the six modes are Cash, Bank Transfer, Vodafone Cash, InstaPay, ECash and WePay; one ledger account per mode, mapped in TASK-E-09 with the accountant (owner, 2026-10-27) | closed |
| OPEN-11 | Staff guideline for setting shipping fees | Manual until defined |
| OPEN-12 | Reservation expiry hours | 24 |
| OPEN-13 | Final item group tree and code prefixes | Two top groups per `05a` (owner: later, 2026-10-26) |
| OPEN-14 | Broadcast audience and consent source. Budget cap ignored for now (DEC-33) | Consent required; cap off |
| OPEN-16 | Digits shown to users: Western (default) or Arabic-Indic | Western |
| OPEN-17 | ~~Owner approval of the Arabic glossary (`19` section 8)~~ Closed: native Egyptian review completed, including the two POS strings (owner, 2026-10-27) | closed |
| OPEN-18 | Do catalogs need English item names for any customer? | Optional English fields |
| OPEN-19 | Deposit deadline | 24 hours |
| OPEN-20 | Is Gallery sellable and which warehouses feed chat availability | Main Inventory and Shop count; Gallery display only |
| OPEN-21 | ~~Return window and cash-refund limit~~ Closed: 14 days; refunds up to the invoice/return total, full or partial, cumulative cap per invoice; manager approval stays for reference-less returns and policy exceptions (owner, 2026-10-26) | closed |
| OPEN-15 | ERPNext roles per employee | Per `05a` section 10 |

## 3. Assumptions
ERPNext 16 on a private VM with admin access; the store has stable LAN and mostly stable internet; staff can use a modern browser; Meta, TikTok and Bosta accounts are or will be available; volumes as in DEC-25.

## 4. Risk register
| Risk | Impact | Mitigation |
|---|---|---|
| Hiding a field breaks a hidden dependency | Wrong stock or accounting | Dependency review, tests under employee accounts, config in git, rollback |
| Third-party POS lacks MOQ and PIN controls | Rule gaps at the counter | Spike decides; build in Ops if needed |
| Store VM or link failure | Counter or chat down | UPS, backups, runbooks, circuit breaker |
| TikTok audit delay or WhatsApp policy changes | Publishing gaps | Upload mode, manual pack, early applications |
| Platform price or API changes | Cost or breakage | Re-verify in Phase 0, pin versions, budget cap |
| Solo-developer capacity | Slippage | Staged gates, strangler rollout, agent-assisted work |
| Wrong units (dozen vs piece) | Stock errors | RULE-UOM, tests TEST-11 and TEST-12 |
| Cosmetics expiry or claims | Compliance and returns | Batch and expiry, FEFO, AI claim guardrail |
| Exposed legacy credentials | Account takeover | P0-01 rotation; Bitwarden plus quarterly rotation (`26`) |

## 5. Change log
v5.3.11 (2026-10-28): E-16 — staff roles and permissions verified on the dev site; POS Next custom DocPerm shadowing documented and fixed by config mirroring (DEC-72).
v5.3.10 (2026-10-27): E-02/E-03 — idempotent config script and baseline applied on the dev site (tax fields hidden, Manufacturing workspace hidden; re-run 0 changes).
v5.3.9 (2026-10-27): Phase E started on the dev stack (DEC-71); E-00 recorded (nothing to retire) and E-01 baseline generated (`erp-field-register.csv`, 28 doctypes, 2,028 rows).
v5.3.8 (2026-10-27): owner confirmed the credential rotation and the n8n webhook check; Arabic review done (OPEN-17 closed); POS Next baseline approved (DEC-70); P0 gate status recorded (`appendix-p0-exit-gate.md`).
v5.3.6 (2026-10-27): E-14b — 11-patch POS Next set applied (defects, `qty*barcode`, offline); baseline approved (DEC-70).
v5.3.7 (2026-10-27): P0-03 automated browser checks — RTL verified, offline failure confirmed, UOM/qty UI defects and the `get_receivable_accounts` bug recorded.
v5.3.5 (2026-10-27): POS Next pinned to `v2.0.0` and the smoke subset re-run on it (21 fields, no F-keys, service-worker scope gap); DEC-68 updated.
v5.3.4 (2026-10-27): ENH-S-02 — Bitwarden chosen as the secrets manager (DEC-69); rotation schedule in `26`.
v5.3.3 (2026-10-26): POS Next fit test partial result (provisional go, DEC-68); `14` verify/unknown cells answered; owner authorised synthetic data on the dev site and deferred hardware; uninstall rehearsal done; hardware/visual checks pending.
v5.3.2 (2026-10-26): OPEN-21 and OPEN-02 closed; DEC-67 records the repository layout.
v5.3.1 (2026-10-26): owner decisions after the P0 review: OPEN-01 closed at 15%; OPEN-02 = Administrator; OPEN-10 and OPEN-13 deferred (defaults hold); OPEN-21 partially answered ("possible total value"); P0-12 skipped because the owner deleted the legacy app (DEC-02); week-1 model bake-off skipped (DEC-66); `docs` agent model replaced with its `21` fallback (`mimo-v2.6-flash`).
v5.3 FINAL (2026-10-22): cost savings adopted (DEC-64, DEC-65), tasks A-10, A-11, ENH-S-10, ENH-S-11, ENH-C-09; tests TEST-101 to TEST-107; running cost estimate lowered.
v5.2 FINAL (2026-10-22): autopilot scripts and permissions, VM guidance, dev and production ERPNext install tasks (DEC-62, DEC-63), cost-saving proposals (`25`).
v5.1 FINAL (2026-10-22): OpenCode Go limits, privacy table and current model IDs applied to `opencode.json` and `21`; step-by-step OpenCode guide added (`23`).
v5.0 FINAL (2026-10-21): per-job model assignments and OpenCode config (DEC-60), WhatsApp invoice sending and one-click broadcast (DEC-58, DEC-59), machine-readable task list, regrouped index; tests TEST-92 to TEST-100; build-ready (DEC-61).
v4.1 FINAL (2026-10-20): merged the owner's v2.3 implementation spec: deposit rule for new resellers, FIFO, two purchasing flows, six payment modes, Gallery warehouse, effective-discount and price-conflict rules, stricter returns, manual couriers (DEC-44 to DEC-54); tests TEST-79 to TEST-91.
v4.0 FINAL (2026-10-17): Arabic and English localization specified (`19`, DEC-39 to DEC-42), tests TEST-67 to TEST-78, package declared final (DEC-43).
v3.4 (2026-10-17): enhancement backlog decided (DEC-37), agent safety rule (DEC-38), onboarding package (`17`) and acceptance scripts (`18`) added; tests TEST-58 to TEST-66.
v3.3 (2026-10-17): scan info card and the owner's key map made required (DEC-36); plain-language scope summary added (`15`).
v3.2 (2026-10-17): feature comparison of the legacy app and POS Next added (`14`); final stack decided (DEC-34, DEC-35); tests TEST-53 to TEST-55 added.
v3.1 (2026-10-17, owner confirmed): the old Desk POS and Diva Sale pilot are retired after POSNext works (DEC-02, DEC-29); `diva_guard` is allowed (DEC-29, DEC-30); internal EAN-13 barcodes are kept (DEC-32). Legacy app reviewed (`13`), POSNext adopted for the counter (DEC-29 to DEC-33), purchase flow and tax questions closed, DEC-02 corrected.
v3.0 (2026-10-16): consolidated specification. Replaces Dev_Plan v1, v2.x and the v2.3 Claude Doc. Incorporates owner decisions D35–D51, the ERPNext simplification review, the POS review, the dozen unit decision, and the new build order.
