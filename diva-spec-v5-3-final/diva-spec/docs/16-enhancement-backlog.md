# 16 Enhancement Backlog and Decisions

Status: **decided 2026-10-17 (DEC-37).** The owner asked the planner to choose. Rule used: accept **all P0 items** and the **P1 items that are cheap and support the ERPNext-then-publishing priority**; defer P2 and expensive P1 items. The owner can change any row; tell the planner the ID. Sizes: S about 6 h, M about 20 h, L about 50 h (agent-assisted estimates).

Accepted: **53 items, about 556 h** (estimate; plan range 80%–125%). Deferred: 25 items.

## Accepted enhancements by phase

| Phase | Items | Effort (h) |
|---|---|---|
| P0 | ENH-R-01, ENH-R-03, ENH-R-04, ENH-S-01, ENH-S-02 | about 30 |
| E | ENH-A-01, ENH-A-02, ENH-A-03, ENH-A-04, ENH-A-05, ENH-A-06, ENH-A-07, ENH-A-10, ENH-C-01, ENH-C-02, ENH-C-03, ENH-C-04, ENH-I-01, ENH-I-05, ENH-I-07, ENH-R-05, ENH-R-06, ENH-R-07, ENH-S-03, ENH-S-09 | about 176 |
| PUB | ENH-M-01, ENH-M-02, ENH-M-03, ENH-M-04, ENH-M-05, ENH-M-06, ENH-M-07, ENH-L-01, ENH-L-02, ENH-L-03, ENH-I-02, ENH-I-04, ENH-K-01, ENH-K-02, ENH-S-04, ENH-S-05, ENH-S-08 | about 186 |
| O | ENH-C-06, ENH-M-08, ENH-S-06 | about 60 |
| C | ENH-H-01, ENH-H-04, ENH-H-05 | about 46 |
| A | ENH-H-02, ENH-H-03, ENH-H-08, ENH-H-10 | about 38 |
| All gates | ENH-R-02 | about 20 |


## Readiness and process

| ID | Item | Why | Phase | Size | Priority | Decision |
|---|---|---|---|---|---|---|
| ENH-R-01 | Agent onboarding package: everything the owner provides (staging ERPNext copy, VM access, repository, secrets manager, Meta, WhatsApp, Bosta, TikTok and Telegram accounts, hardware, item master export) | The agent cannot start without access and sample data | P0 | S | P0 | **Accepted** |
| ENH-R-02 | Owner acceptance scripts: plain-language Arabic test script and sign-off checklist for every phase gate | You are not reading code, so acceptance must be demonstrable | All gates | M | P0 | **Accepted** |
| ENH-R-03 | Pull-request and review checklist: test evidence, staging demo, security checklist, who reviews | Keeps agent output safe and reviewable | P0 | S | P0 | **Accepted** |
| ENH-R-04 | Task template, definition of ready, and decision records (ADR) for the agent | Less guessing, fewer rework loops | P0 | S | P1 | **Accepted** |
| ENH-R-05 | Go-live cutover plan: freeze window, parallel-run days, rollback, communication to staff | Counter must never stop selling | E | M | P0 | **Accepted** |
| ENH-R-06 | Staff offboarding and PIN rotation procedure (disable ERPNext user, revoke tokens and PINs) | Prevents access by former staff | E | S | P0 | **Accepted** |
| ENH-R-07 | Change-management plan: champion cashier, practice mode, quick-reference card | Staff adoption decides success | E | S | P1 | **Accepted** |
| ENH-R-08 | Budget and hours tracker per phase | Cost control with an agent-built project | All | S | P2 | Deferred |
| ENH-R-09 | Feature flags and staged rollout per channel and per rule | Safer releases | PUB | M | P1 | Deferred |
| ENH-R-10 | Anonymized copy of production data for staging and tests | Realistic tests without exposing customer data | P0 | M | P1 | Deferred |

## ERP and accounting

| ID | Item | Why | Phase | Size | Priority | Decision |
|---|---|---|---|---|---|---|
| ENH-A-01 | Opening balances and cutover: stock, customer receivables, supplier payables, cash, bank and wallet balances | Accounting is wrong from day one without them | E | M | P0 | **Accepted** |
| ENH-A-02 | Simple chart of accounts for a trading shop, including owner drawings, expense categories and wallet accounts | Clean books and reports | E | S | P0 | **Accepted** |
| ENH-A-03 | Expired and damaged stock write-off flow with accounts | Needed for cosmetics | E | S | P0 | **Accepted** |
| ENH-A-04 | Monthly accountant pack export: profit and loss, balance sheet, general ledger, receivable and payable aging, stock valuation | Saves hours every month | E | S | P1 | **Accepted** |
| ENH-A-05 | Daily bank and wallet reconciliation checklist (Vodafone Cash, InstaPay, bank) | Catches missing payments | E | S | P1 | **Accepted** |
| ENH-A-06 | Price rounding policy at invoice (for example nearest 1 or 5 EGP) | Avoids odd totals and change problems | E | S | P1 | **Accepted** |
| ENH-A-07 | Petty cash in and out at the till | Cash reconciles at shift close | E | S | P1 | **Accepted** |
| ENH-A-08 | Credit policy for back-office invoices: limits, approval, due dates, reminders | Controls debt risk | E | M | P1 | Deferred |
| ENH-A-09 | Cost-change alert: warn when a buying price rises and margin drops below target | Protects margin | E | M | P1 | Deferred |
| ENH-A-10 | Bulk price update with preview, effective date, audit, and cost-plus markup helper per category | Safe repricing | E | M | P1 | **Accepted** |
| ENH-A-11 | Quotations for large reseller orders (Quotation to Sales Order) | Common in wholesale | O | M | P2 | Deferred |
| ENH-A-12 | Supplier performance: price history and delivery issues | Better buying | G | M | P2 | Deferred |

## Counter and orders at the store

| ID | Item | Why | Phase | Size | Priority | Decision |
|---|---|---|---|---|---|---|
| ENH-C-01 | Offline-sync monitoring for POS Next: alert if unsynced invoices exceed N hours | Prevents silent data gaps | E | S | P0 | **Accepted** |
| ENH-C-02 | Manager PIN security: hashed, lockout after failures, never logged, audited | Protects discounts and overrides | E | S | P0 | **Accepted** |
| ENH-C-03 | Cash drawer opening through the receipt printer; hardware test | Faster cash handling | E | S | P1 | **Accepted** |
| ENH-C-04 | Receipt branding: logo, return policy, opening hours, phone number | Professional receipts, fewer disputes | E | S | P1 | **Accepted** |
| ENH-C-05 | Repeat last order and last prices for registered customers at the counter | Faster repeat buyers | E | M | P1 | Deferred |
| ENH-C-06 | Pickup orders: chat order paid and collected at the store with a pickup code | Common for Cairo resellers | O | M | P1 | **Accepted** |
| ENH-C-07 | Cashier training mode (separate test POS Profile) | Safe practice | E | S | P2 | Deferred |
| ENH-C-08 | Cashier and shift variance reports | Accountability | G | S | P2 | Deferred |

## Inventory

| ID | Item | Why | Phase | Size | Priority | Decision |
|---|---|---|---|---|---|---|
| ENH-I-01 | Cycle-count schedule with variance approval and shrinkage report | Accurate stock | E | M | P1 | **Accepted** |
| ENH-I-02 | Reorder levels and low-stock alerts to Telegram | Avoids stockouts | PUB | S | P1 | **Accepted** |
| ENH-I-03 | Supplier invoice photo to draft Purchase Invoice (AI reading, human confirms) | Cuts data entry for a trader | A | L | P2 | Deferred |
| ENH-I-04 | Photo-to-item intake in Telegram: staff sends photo and name, a draft item with EAN-13 is created and a label queued | Fast catalog growth, feeds publishing | PUB | M | P1 | **Accepted** |
| ENH-I-05 | Near-expiry alerts and markdown suggestions | Reduces cosmetics waste | E | S | P1 | **Accepted** |
| ENH-I-06 | Dead-stock and fast-mover reports with reorder suggestions | Smarter buying | G | M | P2 | Deferred |
| ENH-I-07 | Product data quality dashboard (missing barcode, price, image, pack size) | Publish gate and POS need clean data | E | S | P0 | **Accepted** |
| ENH-I-08 | Bundle and set management with prices | Helps reach order minimums | E | M | P2 | Deferred |

## Publishing and marketing

| ID | Item | Why | Phase | Size | Priority | Decision |
|---|---|---|---|---|---|---|
| ENH-M-01 | Brand voice and Arabic caption style guide used as AI context | Consistent captions | PUB | S | P0 | **Accepted** |
| ENH-M-02 | AI-content labeling and cosmetics-claims policy checklist | Platform and legal safety | PUB | S | P0 | **Accepted** |
| ENH-M-03 | WhatsApp opt-out handling (STOP) and consent audit | Required for marketing messages | PUB | S | P0 | **Accepted** |
| ENH-M-04 | TikTok media pipeline: photo posts first, then video conversion to 9:16 with captions | TikTok needs media the plan did not specify | PUB | M | P0 | **Accepted** |
| ENH-M-05 | Content calendar and scheduled posting | Consistent presence | PUB | M | P1 | **Accepted** |
| ENH-M-06 | Click-to-chat links with campaign codes and post-to-order attribution | Shows which posts sell | PUB | M | P1 | **Accepted** |
| ENH-M-07 | Image standards, platform sizes, logo watermark | Brand and anti-copy | PUB | M | P1 | **Accepted** |
| ENH-M-08 | Price list and catalog PDF or image export per tier, auto-refreshed, sent by chat | Resellers ask for it constantly | O | M | P1 | **Accepted** |
| ENH-M-09 | Instagram Stories and Reels, extra Facebook post types | Reach | PUB | M | P2 | Deferred |
| ENH-M-10 | Google Business Profile for the store | Local discovery | G | S | P2 | Deferred |
| ENH-M-11 | Seasonal promotions calendar with validity dates in price lists and POS offers | Planned campaigns | G | M | P2 | Deferred |
| ENH-M-12 | Post performance dashboard (reach, clicks, orders) | Measures publishing | G | M | P2 | Deferred |

## Chat and AI

| ID | Item | Why | Phase | Size | Priority | Decision |
|---|---|---|---|---|---|---|
| ENH-H-01 | Unknown-contact flow: new reseller screening, spam blocking, rate limits | Protects the inbox and the AI | C | M | P0 | **Accepted** |
| ENH-H-02 | AI conversation review queue with ratings feeding the evaluation set | Quality improves over time | A | M | P0 | **Accepted** |
| ENH-H-03 | AI-written handoff summary for staff | Faster takeovers | A | S | P1 | **Accepted** |
| ENH-H-04 | Unanswered-message alerts and after-hours behavior with next-morning follow-up | No lost leads | C | M | P1 | **Accepted** |
| ENH-H-05 | Canned replies and tags in Chatwoot (complaints, disputes, returns) | Faster, consistent staff replies | C | S | P1 | **Accepted** |
| ENH-H-06 | Reseller profile notes visible to staff and AI | Personal service | A | M | P1 | Deferred |
| ENH-H-07 | Abandoned-cart follow-up inside the messaging window | Recovers orders | A | M | P1 | Deferred |
| ENH-H-08 | Per-conversation AI cost cap and model fallback | Cost control | A | S | P1 | **Accepted** |
| ENH-H-09 | Prompt and model version registry with rollback and comparison | Safe AI changes | A | M | P1 | Deferred |
| ENH-H-10 | Order status self-service in chat (balance for credit customers later) | Fewer staff questions | A | S | P1 | **Accepted** |
| ENH-H-11 | Complaint and dispute workflow with SLA | Protects reputation | C | M | P1 | Deferred |

## Platform, security and resilience

| ID | Item | Why | Phase | Size | Priority | Decision |
|---|---|---|---|---|---|---|
| ENH-S-01 | Dependency and vulnerability scanning in CI (pip-audit, npm audit, secret scanning) | Basic supply-chain safety | P0 | S | P0 | **Accepted** |
| ENH-S-02 | Secrets manager and rotation schedule | Stops repeat of the exposed-credentials problem | P0 | S | P0 | **Accepted** |
| ENH-S-03 | Disaster-recovery targets (data-loss and downtime limits) and restore drills | Defines what safe means | E | S | P0 | **Accepted** |
| ENH-S-04 | Uptime and synthetic checks for counter, webhooks and publishing | You hear about failures first | PUB | S | P0 | **Accepted** |
| ENH-S-05 | Edge protection (Cloudflare or similar): rate limits, WAF, TLS | Public endpoints are attacked | PUB | S | P1 | **Accepted** |
| ENH-S-06 | Pre-launch security review checklist for the cloud node | Catches mistakes before customers do | O | M | P1 | **Accepted** |
| ENH-S-07 | Data subject requests: export and delete reseller data | Personal data law compliance | C | M | P1 | Deferred |
| ENH-S-08 | Audit log retention, export and tamper evidence | Trust and forensics | PUB | S | P1 | **Accepted** |
| ENH-S-09 | Accessibility and right-to-left QA checklist for all front ends | Quality for Arabic users | E | S | P1 | **Accepted** |

## Legal and policy

| ID | Item | Why | Phase | Size | Priority | Decision |
|---|---|---|---|---|---|---|
| ENH-L-01 | Reseller terms in Arabic: minimums, deposit, returns, shipping, cosmetics policy | Prevents disputes | PUB | S | P0 | **Accepted** |
| ENH-L-02 | Privacy notice and consent wording for chat, Mini App and marketing | Compliance | PUB | S | P0 | **Accepted** |
| ENH-L-03 | Cosmetics advertising and product claims review by a professional | Regulatory risk | PUB | S | P1 | **Accepted** |
| ENH-L-04 | Check consumer-protection rules if you ever sell to non-resellers | Scope change risk | G | S | P2 | Deferred |

## Analytics

| ID | Item | Why | Phase | Size | Priority | Decision |
|---|---|---|---|---|---|---|
| ENH-K-01 | KPI definitions and owner dashboard: sales, margin, stock value, receivables, conversion, response time, AI deflection, publishing results | One agreed set of numbers | PUB | M | P1 | **Accepted** |
| ENH-K-02 | Weekly owner summary in Telegram | Low effort, high value | PUB | S | P1 | **Accepted** |
| ENH-K-03 | Reseller segmentation and dormant-reseller reactivation | Growth | G | M | P2 | Deferred |
| ENH-K-04 | Automatic tier upgrades by spend | Reward loyal resellers | G | S | P2 | Deferred |

## Added 2026-10-22 (cost savings, DEC-64)

| ID | Item | Why | Phase | Size | Priority | Decision |
|---|---|---|---|---|---|---|
| ENH-S-10 | Self-hosted Uptime Kuma and GlitchTip for monitoring | Replaces paid monitoring | PUB | S | P1 | **Accepted** |
| ENH-S-11 | Media and backups on Cloudflare R2 or Backblaze B2 with restic and a tested restore | Cheap off-site storage | PUB | S | P1 | **Accepted** |
| ENH-C-09 | "Message us" QR and click-to-chat link on receipts, invoices and the shop sign | Customers message first: free window and free phone verification | E | S | P1 | **Accepted** |

## Why these were deferred
- **P2 items:** nice to have; revisit in Phase G.
- **Expensive P1 items** (reseller notes, abandoned-cart follow-up, prompt registry, dispute workflow, repeat last order, credit policy, cost-change alert, data-subject requests, feature flags, anonymized staging data): valuable but not needed for the first release. Until anonymized staging data exists, restrict staging access to people who may see customer data. Revisit data-subject requests (ENH-S-07) before opening the chat channel to many customers.

## Decisions still needed from the owner before coding

| Before | Open item | Default if unanswered |
|---|---|---|
| Phase E start | OPEN-13 final item group tree | Two top groups per `05a` |
| Phase E start | OPEN-10 ledger account for each payment mode | One account per mode |
| `E-14` | OPEN-04 return policy for opened cosmetics | No returns unless defective |
| `E-14` | OPEN-06 near-expiry threshold | 90 days |
| Phase PUB | OPEN-14 broadcast audience and consent source | Consent required, cap off |
| Phase O | OPEN-03 reseller tiers; OPEN-11 shipping-fee guideline; OPEN-12 reservation expiry | One tier; manual; 24 h |
| Phase C | OPEN-07 WhatsApp provider and Chatwoot compatibility | Found in `P0-07` |

## Planning is finished when

1. The owner chooses which backlog groups join the phases (this file becomes part of `09`).
2. The owner answers or accepts the defaults for the open items above.
3. The owner completes the agent onboarding package (ENH-R-01).
4. The package is frozen as v3.4 and handed to the coding agent.

## Top risks the plan cannot remove

- Item master data quality (barcodes, prices, pack sizes, categories) is the largest hidden effort; ENH-I-07 and `E-01` address it.
- POS Next is young and vendor-controlled; pinning and rehearsals reduce but do not remove the risk.
- Platform rules change (WhatsApp pricing and AI policy, TikTok approval, Meta API versions).
- A solo owner reviewing agent output needs strong acceptance scripts (ENH-R-02).
- Staff adoption: a good system badly adopted fails (ENH-R-07).
- Internet and power reliability at the store (UPS, tested restore, paper fallback).
