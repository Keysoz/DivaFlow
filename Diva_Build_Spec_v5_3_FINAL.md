# AGENTS.md — Rules for any coding agent working on Diva

Applies to Claude Code, Codex, Cursor or any other agent. Read this file first, then `docs/00-index.md`.

## 1. How to work
1. Take one task from `docs/09-build-plan.md` at a time. Use its ID (for example `TASK-O-04`) in the branch name and every commit.
2. Audit before changing: read the relevant docs and the existing code, then state your plan in a short note before editing.
3. Work in small increments. Every increment ships with tests and a Git checkpoint.
4. When you change a file, output the complete file, not fragments, unless the owner asks otherwise.
5. **Never claim a test passed unless you ran it and read the result.** Paste the command and the outcome in your report.
6. If a requirement is ambiguous or an owner decision is missing (see `docs/12-decisions-open-items.md`), stop and ask. Do not guess business rules.
7. When a decision is made, update `docs/12-decisions-open-items.md` in the same change.
8. Keep `CHANGELOG.md` current. Keep a risk register in `docs/12`.

## 2. Hard constraints (never violate)
- **Never modify ERPNext core, and write no code inside ERPNext.** No custom Frappe app, Server Scripts, Client Scripts or custom fields. Configuration stored as data is allowed: workspace and module visibility, Customize Form and Property Setters (hide, default, read-only), role permissions, print formats built with Print Format Builder, price lists, payment terms. Apply it only through the idempotent `infra/erpnext-config` script (see `docs/05a-erp-configuration.md`) so it is versioned and repeatable. **Two governed exceptions (DEC-29):** (1) **POS Next by BrainWise** (`pos_next`, `BrainWise-DEV/POSNext`; never the unrelated older "POSNext" by exvas), pinned to one version, with a small tracked patch set kept in git and an upgrade and uninstall rehearsal on staging before any change (POS Next adds its own custom fields; they are vendor-owned); (2) `diva_guard`, a minimal custom Frappe app containing only server-side validation hooks and its own settings doctypes. Both need tests, never edit core, and add no custom fields. `diva_guard` imports `packages/rules-engine` (pure Python) so rules are not duplicated.
- **No code, workflow or log may contain a secret.** Secrets live in environment variables or a secret manager.
- **Nothing automated may mark a payment as verified.** Only a human with the `payment_reviewer` role, through the API, can do it.
- **All business rules live in `packages/rules-engine`.** The cloud API, local API, POS, Mini App and AI call it. Never reimplement a rule elsewhere.
- **The cloud never calls ERPNext directly.** The cloud uses `apps/local-api`. At the counter, POSNext talks to ERPNext on the store LAN. Staff Ops screens use `local-api`.
- **The AI has no tool that changes price, discount beyond limits, stock, payment status or order status.**
- **Every user-facing string exists in Arabic and English, Arabic is primary and RTL, and nothing is hard-coded.** Follow `docs/19-localization-arabic-english.md`. CI fails on a missing translation key.
- Stock UOM is Nos (piece). Buying, selling and prices are in Dozen (1 Dozen = 12 Nos). Never assume a quantity is in pieces without checking the UOM.
- Money is `Decimal` or integer minor units. Never floating point. Totals and VAT come from ERPNext responses.
- Do not reintroduce Google Sheets as a data store.
- Times are stored in UTC and displayed in Africa/Cairo.

## 3. Definition of Done (every task)
- Acceptance criteria in the task are met and demonstrated by tests you ran.
- Unit tests for new logic; integration tests for new endpoints; contract tests for ERPNext/Bosta/Meta adapters.
- Lint, type checks and the full test suite pass in CI.
- Errors are explicit and actionable. Nothing is silently swallowed.
- Audit log entries exist for sensitive actions.
- Arabic (RTL) and English strings come from i18n files, not literals.
- Docs updated. No secrets. No TODOs left without a task ID.

## 4. Stack and layout
Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, Alembic, pytest, ruff, mypy. PostgreSQL everywhere (also in dev). TypeScript, React, Vite, Vitest, Playwright, pnpm. Docker Compose for both nodes. GitHub Actions or equivalent CI.

```
diva/
  AGENTS.md  CHANGELOG.md
  docs/
  apps/
    cloud-api/      chat, AI, orders, Control Room API, Telegram bot, workers
    local-api/      store gateway and Ops/POS API; only component that talks to ERPNext
    ops-pwa/        Diva Ops and counter POS (React PWA, served by local-api)
    control-room/   management dashboard (React)
    mini-app/       Telegram Mini App (React)
    market-worker/  Telethon price monitor (cloud)
  packages/
    rules-engine/   pure Python business rules, used by cloud-api and local-api
    erpnext-adapter/ typed ERPNext REST client with contract tests
    contracts/      OpenAPI specs and JSON schemas shared by all apps
    ui/ api-client/ auth/ i18n/   shared front-end packages
  infra/            compose files (cloud, store), WireGuard, backup scripts
  tests/            e2e and contract suites
```

## 5. Commands (create in TASK-P0-10; keep stable)
`make setup`, `make dev-cloud`, `make dev-store`, `make test`, `make lint`, `make e2e`, `make contract`.

## 6. Security defaults
Authenticate every endpoint. Verify signatures on every webhook you receive (Chatwoot, Bosta, Telegram). Validate all input. Apply role checks on the server. Log actor, action, target and result for sensitive operations. Mask phone numbers for roles that don't need them.

## 7. Pull request checklist (ENH-R-03)
Every pull request states: the task ID; what changed and why; the commands run and their actual results; screenshots or a short recording for any screen; migrations and rollback; security impact (new endpoints, permissions, secrets); documentation updated; anything uncertain. The owner or reviewer merges, never the agent.

## 8. Task template and decision records (ENH-R-04)
Task: ID, goal, dependencies, acceptance criteria, files likely touched, tests required, rollback. Definition of ready: owner decisions needed are answered or defaulted in `docs/12`. When a design choice is made, add a short decision record to `docs/12` (context, choice, alternatives, consequences).

## 9. Production safety (DEC-38)
Work on dev and staging only. Never hold production administrator credentials. Production changes happen through CI deploys approved by the owner after a fresh backup.

## 10. Use the right agent and model (DEC-60)
Models are assigned per job in `opencode.json` and `docs/21-ai-tooling-policy.md`: `plan` thinks, `build` implements, `frontend` and `frontend-hard` build screens, `tests` writes tests (never the model that wrote the code), `bulk` does repetitive work, `docs` and `arabic` draft text (free models: never give them secrets or real customer data; Arabic strings need native review), `ui-check` looks at screenshots, and `review-by-glm` or `review-by-deepseek` reviews code written by the other vendor. Critical code also needs a Western-vendor review (`prompts/07`).

## 11. Autopilot workflow (run one task end to end)
Use this when started with `scripts/run-task.sh` or `opencode run --agent build "…"`.
1. **Read the task** (ID, dependencies, acceptance criteria) and the spec sections it names. If it needs a human action (credentials, accounts, owner decision, approvals) or a rule is missing, stop and write `BLOCKED: <reason>` followed by exactly what the owner must do. Do not guess.
2. **Branch** `task/<id>-<short-name>` from the latest default branch. Never commit to the default branch.
3. **Plan** briefly (the `plan` agent via the task tool, or your own reasoning) and keep the plan for the pull request description.
4. **Implement** in small commits. Delegate by calling the subagents: `tests` writes tests, `docs` writes documentation, `frontend` builds screens, `arabic` drafts Arabic strings, `bulk` does repetitive edits, `ui-check` inspects screenshots. Use `build-hard` or `plan-hard` only when stuck.
5. **Verify:** run `make lint test` (and `make e2e` when screens change). Fix until green. Quote the real command output; never claim a test passed without running it.
6. **Review:** call `review-by-glm` (or `review-by-deepseek` if GLM wrote the code) with the diff. Fix the findings.
7. **Critical code** (payments, deposits, discounts, `diva_guard`, authentication, backups, migrations, secrets): label the pull request `critical`, do NOT enable auto-merge, and write "CRITICAL REVIEW NEEDED" in the description.
8. **Push and open the pull request** with the template using `gh pr create`. For non-critical work run `gh pr merge --auto --squash`.
9. **Record progress** in `PROGRESS.md` (task ID, pull request link, status) and update `docs/12` and `CHANGELOG.md` if a decision changed.
10. **Final report** in at most 15 lines: done (with evidence), blocked, decisions needed (with your recommendation), next task, risks.

Hard stops: never merge a `critical` pull request; never push to the default branch; never use production credentials; run destructive commands only inside the repository and Docker development containers; if any secret appears anywhere, stop and report it.


---

# Diva Build Specification v5.3 FINAL: Index

Date: 2026-10-22. Status: **final and build-ready.** Build order: P0, E (ERPNext), PUB (publishing), O, B, C, A, M, G. Supersedes every earlier plan. `Diva_Build_Spec_v5_3_FINAL.md` is the same content in one file.

## Start here
| File | Purpose |
|---|---|
| `../AGENTS.md` | Rules and Definition of Done for any coding agent |
| `../opencode.json` | The model assigned to each job |
| `15-agreed-scope-summary.md` | Plain-language list of what will and will not be done |
| `20-start-here.md` | How to start with the agent, first two weeks |
| `24-autopilot-setup.md` | VM, GitHub, OpenCode permissions; run tasks with the fewest manual steps |
| `23-opencode-step-by-step.md` | Detailed OpenCode setup, daily routine, quotas, troubleshooting |
| `17-agent-onboarding-package.md` | What the owner prepares first |
| `../tasks.csv` | Every task with ID, phase, dependencies and acceptance criteria |

## Design
| File | Content |
|---|---|
| `01-scope.md` | Business, users, channels, non-goals |
| `02-architecture.md` | Two-node topology, components, link-down behavior |
| `03-domain-data.md` | Entities, ownership, events |
| `04-business-rules.md` | The rules engine, rule by rule |
| `05-state-machines.md` | Order, payment, shipment, hold, shift |
| `05a-erp-configuration.md` | ERPNext simplification and configuration baseline |
| `19-localization-arabic-english.md` | Arabic and English on every surface |

## Modules
| File | Content |
|---|---|
| `06-modules-core.md` | Gateway, order engine, payments, Bosta, settings, auth |
| `07-modules-apps.md` | Ops, counter POS, Control Room, Telegram admin, Mini App |
| `08-modules-ai-channels.md` | Chat hub, AI agent, media, publishing, market monitor |
| `22-whatsapp-documents-and-broadcast.md` | Send invoices by WhatsApp; one-click broadcast |
| `14-feature-decision-matrix.md` | ERPNext, POS Next, legacy app and Diva Ops: who does what |

## Build, quality, operations
| File | Content |
|---|---|
| `09-build-plan.md` | Phases, task IDs, acceptance criteria, effort |
| `10-quality-security.md` | Test matrix, performance, security, observability |
| `18-owner-acceptance-scripts.md` | Plain-language acceptance steps for every gate |
| `21-ai-tooling-policy.md` | Models and tools, budget, data rules |
| `11-operations-cost.md` | Backups, runbooks, training, running cost |

## Reference
| File | Content |
|---|---|
| `12-decisions-open-items.md` | Decision log, open questions, assumptions, risks, change log |
| `13-legacy-app-review.md` | Review of the old `diva_store` app and retirement plan |
| `16-enhancement-backlog.md` | Accepted and deferred enhancements |
| `25-cost-savings.md` | Proposed ways to get the same features cheaper |

## ID conventions
`TASK-<phase>-<nn>` build tasks; `ENH-<area>-<nn>` enhancements; `I18N-<nn>` localization tasks; `RULE-<area>` business rules; `DEC-<nn>` decisions; `OPEN-<nn>` open owner questions; `TEST-<nn>` test cases.

## Glossary
- **Reseller:** wholesale customer who buys via chat or the Mini App.
- **Counter:** the physical store sales point, served by the store node.
- **Chat order:** order started in WhatsApp, Instagram, Facebook or the Mini App.
- **Cloud node / Store node:** the two deployments (`02-architecture.md`).
- **Gateway:** the `local-api` interface the cloud uses to reach ERPNext safely.
- **Reservation:** ERPNext stock reserved for a confirmed chat order.
- **Proof:** a record of a customer's claimed payment. It is not a verified payment.
- **Rule set version:** version of Settings under which an order was confirmed.
- **Link:** the secure tunnel between the cloud node and the store node.


---

# 15 Agreed Scope Summary (plain language)

What the owner and the specification have agreed will be done, what will not, and what depends on a test. If this file and another file disagree, tell the owner and fix this file.

## 1. Will be done
| Area | What | Phase |
|---|---|---|
| ERPNext simplification | Unneeded modules hidden (Manufacturing, HR and Payroll, Projects, Quality, Assets, CRM, Website, Support). Item, Sales Invoice, Purchase Invoice, Customer, Supplier and stock forms simplified by hiding fields, setting defaults and tightening permissions. Nothing is deleted or uninstalled. Applied by a repeatable configuration script after a field-by-field review of the live site | E |
| Units | Stock in pieces; buying, selling and prices in dozens (1 dozen = 12 pieces) | E |
| Purchasing | Purchase Invoice with Update Stock (goods and invoice arrive together); supplier payables and payments | E |
| Money | Payment modes Cash, Bank Transfer, Vodafone Cash, InstaPay; no VAT, no e-invoicing; expenses and cash tracking | E |
| Counter | POS Next (BrainWise) with a small guard app and a few patches: held sales, shifts, receipts, offline selling, returns | E |
| Counter look and feel | **Scan info card** (name, code, price per dozen, stock) on every scan and **your current keys** (F1 help, F2 customer, F3 quantity, F4 discount, F5 note, F6 delete line, F7 held sales, F8 payment, F9 print, F10 new sale, Ctrl+F search, Ctrl+Delete clear, Ctrl+Z undo, Ctrl+R return) | E |
| Counter rules (enforced on the server) | Minimum quantity in dozens; cashier discount up to 5%, manager PIN above; price must match the price list; no credit or partial payment at the counter | E |
| Staff screens | Diva Ops: Receive (Purchase Invoice), Transfer, Count, Labels (EAN-13), Items and barcodes, Collect, Pack | E |
| Barcodes | Existing internal EAN-13 barcodes kept; generator ported with validation | E |
| Cosmetics | Batch and expiry tracking, first-expiry-first-out, expired stock blocked | E |
| Old app | Reviewed; retired after POS Next works; useful logic ported | E |
| Publishing | Facebook, WhatsApp (broadcast templates and a manual pack), Telegram, Instagram, TikTok | PUB |
| Chat orders | Minimum 3,000 EGP, minimum quantities, shipping fee set by staff, chat stock reservations, payment proof reviewed by a person, link-down pause | O |
| Later phases | Bosta (B), chat inbox (C), AI agent with voice and images (A), Telegram Mini App (M), growth (G) | in that order |
| Safety | Exposed credentials rotated first; no automation ever confirms a payment; no wholesale prices in public posts | P0 and all |

## 2. Will not be done
- A new custom ERPNext app beyond the small guard app, or custom fields of our own.
- Keeping the old Desk POS or the Diva Sale pilot.
- Credit, partial payment or installments at the counter or in chat.
- Automatic payment confirmation by the AI or any workflow.
- VAT or e-invoice features.
- Command palette (Ctrl+K).
- Posting to WhatsApp Channels by unofficial tools (a manual ready-to-post pack is provided).
- TikTok direct posting before TikTok approves the app; TikTok voice messages.
- A broadcast budget cap for now (the setting exists, off).
- Starting Bosta, chat inbox, AI or Mini App before ERPNext and publishing are finished.
- Manufacturing, payroll and HR features.

## 3d. Cost savings adopted (v5.3)
Small cloud server first; "Message us" QR so customers message first and invoices go by the cheapest valid WhatsApp path; fixed logic for routine questions; small AI model first; self-hosted monitoring; media and backups on R2 or B2. Not adopted: dropping n8n; replacing AI backgrounds.

## 3c. Added in v5.0 (2026-10-21)
Send invoices, purchase invoices, receipts and statements to customers and suppliers on WhatsApp besides printing (free link in Phase E, one-click send in Phase PUB, about 0.19 EGP per message); one-click broadcast with a cost preview and free channels first (WhatsApp marketing is about 3.4 EGP per message, so not the cheapest); a model assigned to every job in `opencode.json`.

## 3b. Added in v4.1 (2026-10-20)
China import purchasing (purchase order, partial receipts, landed costs, foreign currency, advances, bank-only); six payment modes (adds ECash and WePay); Gallery warehouse; 30% deposit for new resellers with stock reserved only after verification; invoice and delivery at ready-for-dispatch; FIFO costing; effective-discount and price-conflict enforcement; stricter employee returns; manual couriers. **Not adopted:** Telegram-first ordering and a website storefront (deferred), keeping the old app.

## 3a. Languages
Everything in Arabic and English; Arabic primary with right-to-left layout. Covers ERPNext screens, POS, Ops, dashboard, Mini App, Telegram bot, receipts, invoices, labels, WhatsApp templates, public posts, AI replies (Egyptian Arabic and Franco-Arabic understood) and SOPs. Western digits by default. See `19`.

## 3. Accepted enhancements (53 items, `16`)
All P0 items and 30 chosen P1 items: onboarding package and acceptance scripts; opening balances and a simple chart of accounts; write-offs; manager PIN security; offline-sync alerts; data quality dashboard; accountant monthly pack, wallet reconciliation, price rounding, petty cash and bulk price updates; cash drawer, receipt branding, cycle counts, near-expiry alerts; Telegram photo-to-item intake; content calendar, click-to-chat attribution, image standards, WhatsApp opt-out, TikTok media pipeline, brand voice and cosmetics-claims checks; price-list export and pickup orders; unknown-contact screening, canned replies, after-hours handling; AI review queue, handoff summaries, cost caps and order-status replies; security scanning, secrets manager, edge protection, uptime checks, recovery drills; reseller terms and privacy notice; KPI dashboard and weekly owner summary. Deferred: 25 items (mostly P2).

## 4. Depends on the Phase 0 POS Next fit test
Scan info card and the key map as patches (expected to be possible); the `qty*barcode` shortcut, undo last scan and low-stock tint (added if missing); compatibility with ERPNext 16; a full offline shift; dozen and piece handling. If POS Next cannot meet these with small patches, the counter screen is built in Diva Ops instead.


---

# 20 Start Here: building with an AI coding agent

## 1. The agent: OpenCode (DEC-57, DEC-60)
The harness is **OpenCode** with the OpenCode Go subscription. The repository's `opencode.json` assigns a model to each job (planning, backend, front-end, tests, docs, Arabic text, screenshot checks, reviews). The full table and rules are in `21-ai-tooling-policy.md`. OpenCode reads `AGENTS.md`. A Western-vendor review (Claude Pro, ChatGPT Plus or a free Antigravity tier) is required for payments, deposits, `diva_guard`, authentication, backups and migrations (`prompts/07`). If you later prefer another tool, `AGENTS.md` stays the single brief; `CLAUDE.md` is included for Claude Code.

For the fewest-steps setup (dedicated VM, scripts, autopilot) read `24-autopilot-setup.md` first. For the detailed OpenCode steps (install, connect, routine, quotas, troubleshooting) read `23-opencode-step-by-step.md`.

## 2. Setup (about half a day)
1. Create a private Git repository; protect `main` (pull request and green CI required).
2. Unzip the package into the repository root and commit "Add specification v5.0".
3. Install OpenCode on a dev computer or dev VM, **never on the production VM**. Connect OpenCode Go, run `opencode models`, and confirm every model ID in `opencode.json` exists; replace any missing one with the closest current model (`21`).
4. Set up the secrets manager. Never paste tokens into chats or files (`17`).
5. Prepare the onboarding package (`17`): staging ERPNext copy, accounts, hardware, item export.
6. First session is read-only: paste `prompts/00-session-start.md` with "read the spec and tell me the Phase P0 tasks, the hard constraints and your questions". Check the answers against `AGENTS.md`.

## 3. The working loop (every task)
1. Pick the next task ID from `tasks.csv` (or `docs/09-build-plan.md`). Optionally create GitHub issues with `python3 scripts/create_issues.py --phase P0`. One task, one session, one branch.
2. Paste `prompts/00-session-start.md` with the ID.
3. The agent summarizes and proposes a plan. **You approve before any editing.**
4. It implements in small commits with tests and shows the real command output.
5. It opens a pull request (template included). CI must be green.
6. Review (section 5), then merge yourself. Update `docs/12` if a decision changed.
7. Ask for the daily status (`prompts/06`).

## 4. Suggested first two weeks
**Week 1:** `P0-01` and `P0-02` (rotate credentials, secure old endpoints: `prompts/01`), `P0-10` repository and CI (`prompts/02`), `ENH-S-01`, `ENH-S-02`, `ENH-R-03`, `P0-05` infrastructure measurements, `P0-06` hardware tests (Arabic receipt print test sheet).
**Week 2:** `P0-04` ERPNext verification (`prompts/03`), `P0-12` verify legacy findings, `P0-03` POS Next fit test (`prompts/04`), `P0-08` and `P0-09` data and datasets, `P0-11` TikTok and Meta applications, `I18N-01` glossary.
Then close Gate P0 with `docs/18` and start Phase E at `E-00`.

## 5. Reviewing without reading all the code
- Require: real test output, a demo on staging, the acceptance script for the gate, and a plain-language explanation of every change.
- Use a second agent as reviewer with `prompts/05`.
- Red flags: tests deleted or skipped; secrets in the diff; large unrelated changes; "temporary" shortcuts; claims without output; edits to the hard constraints in `AGENTS.md`; anything near payments, discounts, authentication or `diva_guard`.
- Have a human developer review the security-critical parts at gate time (payments, deposits, `diva_guard`, authentication, backups); 2–4 hours per gate is usually enough.

## 6. Guardrails
Dev and staging only; never production credentials (DEC-38). Fresh backup before any production change. No destructive commands without approval. Keep rule documents (`04`, `05`) changeable only by you. Set a spending limit on the agent account. Keep sessions short and focused.

## 7. If it goes wrong
Shrink the task. Revert to the last good commit. Ask the agent to write what it learned into `docs/12`. Start a fresh session with the same prompt. If two attempts fail, get a human developer to look.

## 8. This week
1. Choose the agent and create the repository.
2. Start the onboarding package (`17`).
3. Run `P0-01` yourself: rotate the exposed credentials.
4. Run the read-only first session and the `P0-10` repository task.


---

# 24 Autopilot Setup: VM, GitHub, OpenCode, Fewest Manual Steps

## 1. Where to run it: use a dedicated Linux VM (DEC-62)
You want to give the agent broad access. Give it a **disposable development VM**, not your laptop's own operating system. Reasons: a mistake cannot touch your personal files or accounts; you can snapshot and roll back; Docker and ERPNext need RAM and disk that a VM can reserve; the VM keeps working when your laptop sleeps.
| Option | When | Cost |
|---|---|---|
| Local VM (VirtualBox, KVM or similar) on your Linux laptop | The laptop has 16 GB RAM or more | $0 |
| Small cloud VM | Less RAM at home, or you want it always on | about $10–20 per month |
Size: 4 vCPU, 8–16 GB RAM, 80–100 GB disk, **Ubuntu 24.04 LTS**.
**Run OpenCode inside the VM** (not on the laptop controlling the VM remotely). You connect from the laptop with SSH, ideally inside `tmux` so tasks keep running if the connection drops. No personal keys on the VM: use one GitHub login for the project only. The VM never holds production credentials (DEC-38).

## 2. One-time setup (about 30–45 minutes)
1. Create the VM, then `ssh` in.
2. `git clone` your private repository (it already contains this package) and `cd` into it.
3. `bash scripts/bootstrap-dev-vm.sh`: installs git, GitHub CLI, Docker, Node, pnpm, Python 3.12 (through `uv`), ffmpeg, tmux, OpenCode and the Antigravity CLI. Log out and back in once.
4. `gh auth login` (use the device-code option and approve it in a browser).
5. `opencode`, then type `/connect`, choose **OpenCode Go**, paste your key. Run `opencode models` and compare the IDs with `opencode.json` (`23`).
6. `agy` and sign in with Google (this is the free Western-vendor reviewer; its free tier is small, about 20 agent requests a day, so use it only for critical reviews).
7. `bash scripts/setup-github.sh`: turns on auto-merge, squash merges, labels and branch protection (private repositories need a paid GitHub plan for protection; the script tells you if it cannot).
8. `bash scripts/start-dev-erpnext.sh`: starts a disposable ERPNext demo at port 8080 (Administrator / admin) for development and tests. You do not need to install ERPNext yourself.

## 3. Running the build
- Start `tmux new -s diva`.
- One task: `bash scripts/run-task.sh P0-10`. OpenCode plans, implements, calls the specialist agents, runs the tests, asks the other-vendor reviewer, pushes a branch and opens a pull request. You read the final report.
- Non-critical pull requests merge themselves when CI passes (auto-merge). **Critical** ones wait for you: run `bash scripts/critical-review.sh <branch>`, then read the result and merge.
- Create issues from the task list if you like: `python3 scripts/create_issues.py --phase P0 --create`.

## 4. Do I switch models, tabs and mentions myself?
Not for autopilot. Each agent has its own fixed model (`opencode.json`). `scripts/run-task.sh` starts the `build` agent; `AGENTS.md` section 11 tells it to call the specialist subagents by name for tests, docs, screens, Arabic text, screenshots and reviews. Switching with Tab and typing @mentions is only for interactive sessions when you want to steer. The agent may occasionally skip a delegation; the pull request checklist and the reviewers catch it.

## 5. What stays manual
- Rotating the exposed credentials on each platform (`P0-01`).
- Creating third-party accounts and approvals (Meta, WhatsApp, TikTok, Bosta, domain).
- Your acceptance scripts at each gate (`18`) and Arabic wording review.
- Merging `critical` pull requests.
- Any task the agent reports as `BLOCKED`.

## 6. Permissions and safety
`opencode.json` allows edits and shell commands so runs do not stop for approval, and denies force pushes, pushes to the default branch, `rm -rf /` style commands and manual merges (only `gh pr merge --auto` is allowed). Test the rules once with a harmless command. For a hard guarantee that the agent cannot merge critical work, use a separate GitHub bot account with write access and require your approval on the default branch (optional).

## 7. Cheaper ways to get the same features
See `25-cost-savings.md`.


---

# 23 OpenCode Step by Step

Read `24-autopilot-setup.md` first (dedicated VM and scripts). Facts checked against OpenCode's documentation on 2026-10-22. Commands and menus can change; if something differs, trust OpenCode's own docs and tell the planner.

## A. What to prepare
**Accounts**
1. A GitHub account and a **private** repository for the project.
2. An OpenCode Console account (`https://opencode.ai/console`). Subscribe to **Go ($10)** to start; move to **Go Plus ($40)** when Phase E coding begins. Add billing details and copy your API key. Go plans are for a single-member workspace (your Personal workspace).
3. Optional but recommended: add a small credit balance in the Console and switch on **Extra usage** so work is not blocked when a model's limit is reached; set a Budget.
4. For critical reviews: a free Antigravity tier, or Claude Pro or ChatGPT Plus ($20) when needed.
5. A password manager or secrets manager (`17`).

**Computer and tools**
- A development computer (macOS, Linux or Windows) with a terminal. **Never the production server.**
- Git installed. Docker Desktop (the project runs in containers). Python and Node are set up by the agent; install only from official sources.
- If Linux-only tools (such as `make`) give trouble on Windows, use WSL2.

**Project material:** the unzipped `diva-spec` folder; the onboarding package from `17` (staging ERPNext copy, item export, accounts, hardware).

**Time and money:** about 2–3 hours for setup. $10 to start (Go), $40 from Phase E, plus $0–20 for the critical reviewer.

## B. Install OpenCode
Pick one command:
- macOS or Linux: `curl -fsSL https://opencode.ai/install | bash` or `brew install opencode`
- Any system with Node: `npm i -g opencode-ai@latest`
- Windows: `scoop bucket add extras` then `scoop install extras/opencode`, or `choco install opencode`
Open a new terminal and run `opencode` in any folder to check it starts.

## C. Connect OpenCode Go
1. Run `opencode` inside your project folder.
2. Type `/connect`, choose **OpenCode Go**, paste your API key.
3. Type `/models` to see and choose models. From the terminal you can also run `opencode models` (and `opencode models --refresh`) to list exact IDs. Go models are written `opencode-go/<model-id>`.
4. Compare the IDs in the repository's `opencode.json` with that list. If an ID is missing, replace it with the closest current model and note the change in `docs/12`.

## D. Set up the project
1. Create the private repository on GitHub and clone it to your computer.
2. Unzip the package into the repository root so `AGENTS.md`, `opencode.json`, `docs/`, `prompts/` and `tasks.csv` are at the top.
3. Commit and push: "Add specification v5.1".
4. In GitHub, protect `main` (changes need a pull request and a passing check).
5. **Do not run `/init`**: `AGENTS.md` already exists and is the project brief. OpenCode reads it.
6. Open `opencode.json` and check that the model IDs match `opencode models`.

## E. Your first session (read-only, about 20 minutes)
Run `opencode --agent plan` in the repository. Paste:
> Read AGENTS.md and docs/00-index.md. Do not edit anything. Tell me: the hard constraints, the build order, the Phase P0 tasks, which agent you will use for each kind of job, and any questions you have.
Check the answer against `AGENTS.md` and `docs/21`. If it misses a hard constraint, stop and fix the setup before any coding.

## F. The routine for every task
1. **Pick a task** from `tasks.csv` (or create GitHub issues with `python3 scripts/create_issues.py --phase P0 --create`). One task, one session, one branch.
2. **Plan:** start `opencode --agent plan`, paste `prompts/00-session-start.md` with the task ID. Read the plan. Reply "approved" or ask for changes. You approve before any editing.
3. **Build:** press **Tab** to switch to `build`. Say: "Implement the approved plan in small commits. Then use @tests to write tests from the acceptance criteria, run the tests and linters, and show me the exact output."
4. **Specialists:** call them with an @ mention: `@frontend` for screens, `@arabic` for Arabic strings, `@docs` for documentation, `@bulk` for repetitive edits, `@ui-check` for screenshots, `@build-hard` or `@plan-hard` only when stuck.
5. **Review:** say "@review-by-glm review the changes on this branch against AGENTS.md and the task's acceptance criteria. Do not edit files." (Use `@review-by-deepseek` if GLM wrote the code.)
6. **Critical code** (payments, deposits, `diva_guard`, login, backups, migrations): also run `prompts/07-critical-review.md` in a Western-vendor tool before merging.
7. **Pull request:** push the branch, open a pull request with the template, wait for green CI, check it against the acceptance script in `18`, then merge it yourself.
8. **Status:** ask for the daily status (`prompts/06`). Start a **new session** for the next task: `opencode -c` continues the last one, so use it only within the same task.

## G. Keep quotas and cost under control
- Go has a monthly limit **per model**. Volume work is on high-quota models (DeepSeek V4.1 Flash, MiMo-V2.6-Flash, Qwen3.7 Plus); strong low-quota models (GLM-5.3, Kimi K3, DeepSeek V4 Pro) are for planning, hard problems and reviews (`21` section 7).
- Check usage in the Console and with `opencode stats --models`.
- When a limit is hit: use the fallback model, enable Extra usage, or work on a free model for non-sensitive jobs. Upgrade to Go Plus if limits slow you for more than a week.
- Keep sessions focused; huge conversations use more requests.

## H. Safety on your computer
- Keep OpenCode's permission prompts on for commands that delete, deploy or touch the network; never approve "allow everything" blindly.
- Work in the dev folder only. No production credentials or `.env` files with real secrets in the repository; secrets live in the secrets manager.
- Never paste tokens or customer data into the chat. Free and paid models get code and anonymized data only (`21` section 4).
- Commit often. If the agent goes wrong, revert to the last good commit.

## I. Troubleshooting
| Problem | What to do |
|---|---|
| "Model not found" | `opencode models --refresh`, pick the closest ID, update `opencode.json` |
| Provider not connected | Run `/connect` again and paste the key |
| Config error on start | Read the message; compare the keys with OpenCode's agents documentation; fix `opencode.json` |
| A limit reached | Use the fallback model in `21`, enable Extra usage, or wait for the 5-hour window |
| The agent ignores the rules | Stop; ask it to re-read `AGENTS.md`; start a fresh session with `prompts/00-session-start.md` |
| The agent loops or breaks things | Revert to the last commit; shrink the task; try `@build-hard` once; if two attempts fail, ask a human developer |
| A suspicious change touches secrets or payments | Stop; do not merge; run the critical review |

## J. Your first week
1. Day 1: do sections A to E. Rotate the exposed credentials yourself (`P0-01`); the `prompts/01` checklist guides you.
2. Day 2: `P0-10` repository and CI.
3. Days 3 to 5: `P0-04` ERPNext verification, `P0-12` legacy checks, hardware tests.
4. Day 6 to 7: `P0-03` POS Next fit test, applications for TikTok and Meta, glossary draft. Then close Gate P0 with `18`.


---

# 17 Agent Onboarding Package (ENH-R-01)

What the owner prepares before the coding agent starts. The agent works on **development and staging only**. It never receives production administrator credentials (DEC-38).

## 1. Accounts and access
| # | Item | Needed by | Notes |
|---|---|---|---|
| 1 | Private Git repository, branch protection, CI enabled | P0-10 | Agent works on branches; the owner merges |
| 2 | Secrets manager account (for example Doppler, 1Password or SOPS with age) | P0 | Never paste secrets in chat or files |
| 3 | Cloud VPS account and region (decided in P0-05) | P0-05 | Dev and staging first |
| 4 | **ERPNext:** you do not need an existing site. `P0-04a` installs a disposable dev instance and `E-00a` installs production. If an old site exists, a restored copy helps `P0-12` (optional) | P0-03, P0-04 | Customer data is real until anonymized; restrict access |
| 5 | Secure access to the store VM for staging work (WireGuard or Tailscale) | P0 | No production admin for the agent |
| 6 | Item master export (CSV): code, name, group, barcode, price, pack, image | P0-09 | Basis for the field register and data quality |
| 7 | New Telegram bot token (the old one is exposed) | P0-01 | Create after rotating |
| 8 | Meta Business Manager access for testing; Facebook Page and Instagram professional account linked | P0-07, PUB-07 | Add the developer as tester or admin |
| 9 | Current WhatsApp Business API provider access and template list | P0-07 | Needed for Chatwoot compatibility |
| 10 | TikTok developer account and app | P0-11 | Audit takes time |
| 11 | Bosta business account and staging API key | B | Needed later |
| 12 | Domain name and DNS access | PUB-01 | Webhooks and dashboards |
| 13 | Hardware reachable for tests: barcode scanner, 80 mm receipt printer, label printer, a counter PC | P0-06 | Record model numbers |
| 14 | 100 anonymized chats and 50 voice notes | P0-09 | Remove names, phones, addresses |
| 15 | Environment facts (last known): ERPNext 16.30.0, Frappe 16.29.0, site `erp.divastore.local`, bench `~/diva-erp/frappe-bench`, private Debian VM. **Verify on the real machine before relying on them** | P0-04 | |
| 16 | China supplier list with currencies, typical order and payment pattern (40% and 60%), freight and customs cost types | E-08b | |
| 17 | Current valuation setting and stock history export | E-07 | For the FIFO audit |

## 2. Business material
Logo and colors; brand voice notes and 10 sample captions you like (ENH-M-01); reseller terms (ENH-L-01); privacy and consent wording (ENH-L-02); return policy for opened cosmetics (OPEN-04); item group tree (OPEN-13); price tiers (OPEN-03); opening balances sheet (ENH-A-01); list of staff with roles and PIN holders (OPEN-02).

## 3. Working agreement
- One channel for questions (for example a shared chat) and a daily written status from the agent.
- The agent asks instead of guessing when a business rule is missing.
- The owner reviews with the acceptance scripts in `18-owner-acceptance-scripts.md` and signs each gate.
- Nothing is deployed to production without the owner's approval and a fresh backup.

## 4. Agent safety rules
No production credentials. No destructive commands (drop, delete, truncate) without a backup and explicit approval. No real customer messages sent from dev or staging. Use test accounts. Report every secret that appears anywhere so it can be rotated.


---

# 01 Scope

## Business
Diva Store, Egypt. Sales in EGP; China import purchases may use a foreign currency. An **on-site wholesale shop** that buys from traders and sells to traders. **All buying and selling is by the dozen (1 dozen = 12 pieces)**; there is no manufacturing. Categories: **women's accessories and jewelry** and **makeup and cosmetics**. Initial area Cairo and Giza, with nationwide shipping through Bosta for chat orders. Team: owner, manager, two employees. ERPNext 16 on a private VM at the store.

## Owner priority (DEC-03)
1. **ERPNext**: simplified, in dozens, with purchasing, counter sales and POS, payments, accounting, reports, printing, permissions.
2. **Publishing** to Facebook, WhatsApp, Telegram, Instagram and TikTok.
3. Everything else: chat orders, Bosta, Chatwoot hub, AI agent, Mini App, growth features.

## Sales channels
| Channel | Who | Phase |
|---|---|---|
| Counter (physical) | Walk-in and registered wholesale customers | E |
| Publishing: Facebook, WhatsApp, Telegram, Instagram, TikTok | Public and opted-in audiences | PUB |
| Chat orders (WhatsApp, Instagram, Facebook Messenger) | Resellers | O, then C (human-first) and A (AI) |
| Telegram Mini App | Approved resellers | M |
| TikTok DM | Resellers | G |
| Telegram admin bot | Owner and staff | From PUB |

## Users and roles
`owner`, `manager`, `cashier`, `warehouse`, `accounts`, `payment_reviewer`, `sales`, `catalog_manager`, `integration`. The owner can hold all roles initially. Role matrix in `07-modules-apps.md`; ERPNext role mapping in `05a-erp-configuration.md`.

## Volumes (planning basis)
30–100 chats per day, 20–60 counter invoices per day. Size infrastructure for three times this.

## Languages (DEC-39)
Arabic and English everywhere, **Arabic primary** with RTL. Per-user language; resellers detected per conversation. Full specification in `19-localization-arabic-english.md`.

## Goals
1. A simple, fast ERPNext that staff learn quickly, with unneeded modules and fields hidden.
2. Accurate stock, purchasing, sales, payments, debts and reports in dozens.
3. Fast counter sales by barcode with correct accounting.
4. Add a product once; publish to every channel after one approval.
5. Resellers order through chat with rules enforced in code.
6. AI answers within strict guardrails and hands off cleanly.
7. Correct ERPNext orders and Bosta shipments with no duplicates.
8. One dashboard for the owner and manager.

## Non-goals (v3)
- AI or automation confirming payments, ever.
- Credit or partial payment at the counter (DEC-14).
- Installments in chat or by the AI (staff back-office only).
- Unofficial WhatsApp or TikTok automation that risks accounts.
- A custom accounting or inventory system alongside ERPNext.
- Microservices or Kubernetes.
- A browser-side offline invoice queue at the counter.
- Manufacturing, payroll and HR features.

## Assumptions to confirm (see `12`)
Hardware models, WhatsApp provider, e-invoicing and VAT treatment, tier definitions, cosmetics return policy, purchase flow, account mapping for payment modes.


---

# 02 Architecture

## 1. Topology (DEC-05: split deployment)

```
Resellers ─► WhatsApp / Instagram / Facebook ─► Chatwoot (cloud)
                                                   │ webhook
CLOUD NODE (VPS)                                   ▼
 cloud-api (FastAPI + workers) · Postgres+pgvector · Chatwoot · n8n
 Control Room · Mini App · Telegram admin bot · object storage
 AI orchestrator · content publisher · Bosta client · market-worker
            │  WireGuard tunnel (the Link), cloud ──► store only
            ▼
STORE NODE (private VM, LAN)
 local-api (gateway + Ops/POS API) · local Postgres · ops-pwa
 ERPNext 16 + MariaDB + Redis (reachable ONLY by local-api)
 Counter terminals (browser): scanner, receipt printer, label printer
```

The counter works whenever the store LAN works, even with no internet. Chat, AI and publishing need the internet.

## 2. Components
| Component | Node | Responsibility |
|---|---|---|
| `cloud-api` | Cloud | Conversations, resellers, carts, order state machines, payment ledger, Bosta, content, AI orchestration, Control Room API, Telegram bot, outbox and jobs |
| `local-api` | Store | **Gateway** for the cloud; ERPNext adapter; Ops API; item and barcode service; override audit mirror; barcode cache |
| POSNext | Store (inside ERPNext's bench) | Counter POS: scanning, drafts, shifts, payments, receipts. Talks to ERPNext directly on the LAN |
| `diva_guard` | Store (inside ERPNext) | Server-side validation hooks (MOQ, discount limits, price integrity, no counter credit) and the `Diva Product Rule` doctype |
| `ops-pwa` | Store (served by local-api) | Staff screens: Receive, Transfer, Count, Collect, Labels, Items, Pack |
| `control-room` | Cloud | Management dashboard |
| `mini-app` | Cloud | Reseller catalog and checkout |
| `rules-engine` | Both (shared package) | Pure business rules |
| Chatwoot | Cloud | Channel owner and shared inbox |
| n8n | Cloud | Schedules, briefs, alerts only |
| ERPNext | Store | Items, stock, prices, customers, Sales Orders, invoices, payments, accounting |

## 3. Gateway contract (cloud → local-api)
All calls carry an idempotency key, a request ID and a service token over the Link. Responses are typed. Endpoints (OpenAPI in `packages/contracts`):
- `GET /gateway/health`
- `GET /gateway/availability?skus=` returns available-to-promise per SKU
- `POST /gateway/orders` create-or-get a Sales Order by `external_ref` (stored in standard `po_no`)
- `POST /gateway/orders/{ref}/confirm` submit with stock reservation
- `POST /gateway/orders/{ref}/ready` create the Delivery Note and Sales Invoice and allocate the deposit advance
- `POST /gateway/orders/{ref}/release` cancel and release reservation
- `POST /gateway/payments/draft` create a draft Payment Entry
- `GET /gateway/changes?cursor=` change feed for items, prices, stock, barcodes, product rules, customers
- `POST /gateway/shipments/mark` record a shipment reference on the order

The cloud keeps a read-only cache built from the change feed (nightly full reconcile). The cache serves browsing and AI answers. **Every order, price and stock check that matters is revalidated through the gateway.**

## 4. Link-down behavior (DEC-06)
- The cloud pings `GET /gateway/health` every 15 s. After 3 failures (about 45 s) the circuit opens: state `store_offline`. After 3 consecutive successes it closes.
- While `store_offline`: no new orders, carts or confirmations are created. The AI and staff reply with the configured notice that ordering is paused briefly. Browsing answers may continue with a notice that prices and stock may be outdated. Payment proofs may still be received.
- The owner gets a Telegram alert on open and on close. The dashboard shows a banner and a list of conversations to follow up.
- Orders already created are reconciled by `external_ref` when the link returns. Never retry a gateway write without checking by `external_ref` first.
- Sample notice (ar): "الطلبات متوقفة مؤقتاً لعطل فني بسيط، وهنرجعلك أول ما يتحل."

## 5. Counter independence
Counter sales run on POSNext against ERPNext on the store LAN; `ops-pwa` talks only to `local-api`. Neither depends on the cloud. `product_rules` (MOQ, step, publish flags) are mastered in ERPNext as the `Diva Product Rule` doctype owned by `diva_guard`, and replicated to the cloud through the change feed, so MOQ is enforced at the counter even with no internet. Rule enforcement at the counter happens in `diva_guard` hooks at invoice validate and submit, so it cannot be bypassed from the browser.

## 6. Data flow summary
Items, stock, prices, barcodes: ERPNext → local-api → change feed → cloud cache. Orders: cloud → gateway → ERPNext. Counter sales: ops-pwa → local-api → ERPNext. Payments: proof in cloud → human verifies → draft Payment Entry via gateway → accounts submits.

## 7. Environments
`dev` (Docker Compose, both nodes, Postgres, a staging ERPNext copy), `staging` (mirrors production, test Meta/Bosta accounts), `prod`. Separate credentials per environment. Staging ERPNext holds realistic data.

## 8. Security boundaries
ERPNext private to the store LAN. The Link is the only path between nodes. Each staff member has an ERPNext user; `local-api` holds their API credentials encrypted and uses them for their actions (DEC-09). Fallback: integration user with the actor stamped in remarks. Webhooks verified by signature. Media in private object storage with signed, expiring URLs.

## 9. Resilience rules
Durable inbound events before processing. Transactional outbox for outgoing side effects. Dead-letter queue visible in the dashboard. Reconcile-before-retry for every external write. Idempotency keys on every command. Stale AI replies are discarded if a human took over during generation.


---

# 03 Domain and Data

## 1. Ownership
| Entity | Master | Replicated to |
|---|---|---|
| Item, SKU, barcodes, UOM, pack, batch/expiry | ERPNext | Cloud cache (read-only) |
| Stock, reservations | ERPNext | Cloud cache |
| Price lists, tiers, quantity breaks | ERPNext | Cloud cache |
| Customer business record, credit limit, payment terms template | ERPNext | Cloud cache |
| `product_rules` (MOQ, step, max, scope, publish status) as `Diva Product Rule` | ERPNext (doctype owned by `diva_guard`) | Cloud cache via change feed |
| Reseller approval, tier mapping, channel identities, payment policy | cloud-api DB | ERPNext Customer created on approval |
| Conversations and messages | Chatwoot + cloud-api | none |
| Carts, draft orders, order/payment/shipment state | cloud-api DB | ERPNext Sales Order holds the commercial order |
| Sales Order, Delivery Note, Sales Invoice, Payment Entry | ERPNext | cloud shows status |
| Payment proofs and verification ledger | cloud-api DB | draft Payment Entry in ERPNext |
| Held counter sales, shifts, price/discount override audit | local-api DB | summaries to cloud |
| Shipments, tracking | Bosta, mirrored in cloud-api | |
| Posts and publish status | cloud-api DB | |
| Price observations | cloud-api DB | |
| Settings and rule versions | cloud-api DB (master) | local-api (replicated) |

No custom fields in ERPNext (DEC-04). The order reference lives in the standard `po_no` field.

## 2. Core tables (cloud-api)
`resellers`, `reseller_identities`, `conversations`, `messages`, `media_assets`, `carts`, `cart_lines`, `orders`, `order_lines`, `order_events`, `payment_proofs`, `payment_ledger`, `shipments`, `shipment_events`, `outbox`, `inbound_events`, `dead_letters`, `posts`, `post_targets`, `price_observations`, `settings_versions`, `audit_log`, `catalog_cache_*`.

## 3. Core tables (local-api)
`override_audit` (mirror), `barcode_cache`, `label_jobs`, `sync_cursor`, `audit_log`. Held sales and shifts live in POSNext and ERPNext POS entries.

## 4. Key fields
- `orders`: `id` (ULID, also `external_ref` as `DS-<ULID>`), `channel` (counter/chat/miniapp), `reseller_id`, `order_state`, `payment_state`, `shipment_state`, `goods_subtotal`, `discount_total`, `shipping_fee`, `grand_total`, `rule_set_version`, `price_snapshot`, `erp_sales_order`, `created_by`, timestamps.
- `payment_ledger` (append-only): `order_id`, `kind` (proof/deposit/full/cod_collected/cod_remitted/refund), `amount`, `mode`, `reference`, `proof_id`, `actor`, `verified_by`, `verified_at`, `note`.
- Held sales are POSNext draft invoices (no separate table).
- `product_rules`: `item_code`, `min_qty`, `qty_step`, `max_qty`, `moq_scope` (family/variant), `publish_status`.

## 5. Identifier rules
ULIDs for application IDs. Never derive IDs from timestamps. ERPNext names are stored, never constructed. Barcodes are internal EAN-13 numbers in GS1's in-store range (prefix 20–29), as the legacy app already generates; **existing barcodes are kept**. New items get an internal EAN-13 as item code and barcode (DEC-32). Supplier EAN codes are extra barcodes; pack barcodes use UOM conversion.

## 6a. Names and languages
`item_name` is the Arabic name. English name, bilingual descriptions and keywords are fields of the `Diva Product Rule` doctype (`name_en`, `description_ar`, `description_en`, `keywords`). Resellers store `preferred_language` (`ar` or `en`). See `19`.

## 6. Units
Stock in Nos (piece); trading and prices in Dozen (12). `product_rules` quantities are in dozens. Store the UOM next to every quantity in APIs and events.

## 7. Domain events (outbox)
`order.created`, `order.confirmed`, `order.expired`, `order.cancelled`, `payment.proof_received`, `payment.verified`, `payment.refund_requested`, `shipment.created`, `shipment.status_changed`, `catalog.changed`, `store.link_opened`, `store.link_closed`, `ai.handoff_requested`. Each event has an ID, version, timestamp and actor and is consumed idempotently.


---

# 04 Business Rules

All rules are implemented once in `packages/rules-engine` as pure functions with unit tests. Rules read configuration from versioned Settings (`rule_set_version`). Failures return structured errors, for example `{"rule":"min_total","required":3000,"current":2550,"gap":450}`.

## RULE-UOM (DEC-20)
1. Stock UOM is **Nos** (piece). **Dozen** is a UOM with conversion 12. Purchase UOM and Sales UOM are Dozen. Item prices are per Dozen.
2. Sales and purchases are entered in whole dozens (the Dozen UOM is configured as whole-number). Piece-level quantities (returns of single defective pieces, counts, adjustments) use Nos.
3. A dozen barcode carries UOM Dozen; a piece barcode carries UOM Nos. Scanning a dozen barcode adds 1 Dozen.
4. `min_qty`, `qty_step`, MOQ and `max_qty` are expressed in dozens.
5. Reports show dozens for trading and pieces for stock counts. Never mix without stating the unit.

## RULE-MOQ (DEC-07)
1. Each product has `min_qty` and `qty_step` (pack size) in `product_rules`. MOQ scope is the product family with an optional per-variant override.
2. A line must satisfy `min_qty` and be a multiple of `qty_step`, both in dozens (RULE-UOM).
3. **Applies to chat orders and counter sales.**

## RULE-MIN (DEC-07)
1. `goods_subtotal` (authoritative prices, after line discounts, before shipping) must be at least `MIN_ORDER_TOTAL_EGP` (default 3000).
2. **Applies to chat orders only.** It does not apply at the counter.
3. When short, return the gap and suggest items that fit it (best sellers, same category, previously bought).

## RULE-PRICE
1. Price source order: customer-specific price list, then the reseller's tier price list, then the standard list. ERPNext's pricing engine computes it.
2. Prices are fetched at validation and at confirmation. Cart prices are display only.
3. A price snapshot is stored when the order is confirmed. A price that changed during checkout is shown and reconfirmed.
4a. **Conflicts are resolved deterministically (DEC-51):** a valid approved customer-specific price beats the customer-group price list, which beats the channel default list. Expiry dates and quantity breaks are honored. If two rules at the same level still conflict, the sale is blocked for manager review. The price source used is logged on the line.
4. The last price sold to the customer for the item is shown to cashiers and available to the AI as a tool result.
5. Public posts never show wholesale prices; they show MOQ and "reseller price in catalog or chat" (DEC-10).

## RULE-DISC (DEC-13)
| Role | Maximum discount without approval |
|---|---|
| cashier | 5% |
| manager | configurable, default 15% |
| owner | unlimited |
**The limit applies to the effective discount (DEC-50):** (price-list subtotal minus net subtotal) divided by price-list subtotal, so lowering an item rate or stacking line and invoice discounts cannot bypass it. It is enforced on the server for POS and standard invoices, whatever the source. Above a role's limit needs a manager PIN (or owner PIN). Each discount and price override stores actor, reason, amount and approver in `override_audit`, and triggers an owner alert above a configured threshold. The AI may offer only discounts allowed by tier rules (`max_discount_pct` per tier); code enforces it.

## RULE-CREDIT (DEC-14)
1. **No credit and no partial payment at the counter.** Counter sales are paid in full (cash or non-cash).
2. Credit and installments exist only as back-office invoices created by the manager for approved resellers with an ERPNext credit limit, using Payment Terms Templates. The AI and chat checkout never offer them.
3. ERPNext's credit limit check is the enforcement point. Exceeding needs an owner override, logged.

## RULE-PAY
1. No automation or AI may verify a payment. A customer message or screenshot only creates a `payment_proofs` record (method, claimed amount, reference, image hash) and notifies staff.
2. A user with `payment_reviewer` verifies in the Control Room. Verification writes the ledger, then the gateway creates a **draft** Payment Entry. An authorized user submits it in Ops.
3. Methods: Cash, Vodafone Cash, InstaPay, bank transfer, COD (chat orders only, per payment policy).
4. Payment policy per reseller: `deposit_30` (default for **new resellers**: 30% of the eligible goods subtotal after discounts, excluding shipping and taxes), `prepaid_only`, `cod_allowed`. COD unlocks after 3 completed orders with no disputes (configurable). A deposit is recorded as a **customer advance** (Payment Entry against the Sales Order), never as sales revenue, and is allocated to the Sales Invoice at ready-for-dispatch. Example: goods subtotal 4,000 EGP gives a 1,200 EGP deposit and 2,800 EGP goods balance, plus the staff-set shipping fee (DEC-44).
5. The ledger is append-only. Corrections are new entries.
6. Flag proofs with mismatched amount, reused reference or duplicate image hash.

## RULE-SHIP (DEC-12)
1. Shipping fee is decided **per order by staff**. The AI never quotes shipping.
2. A validated chat order moves to `awaiting_shipping_quote`. Staff set the fee, then the final total is sent for reseller confirmation.
3. Shipping is excluded from the 3,000 EGP minimum and included in the COD amount.
4. COD amount equals the order total minus verified prepaid amount.
5. Addresses resolve to Bosta city/zone/district IDs and are confirmed with the reseller before shipment creation.

## RULE-STOCK (DEC-08)
1. Available-to-promise equals ERPNext actual stock in sellable warehouses minus reservations.
2. **Chat reservations are protected, and they follow the payment policy (DEC-44).** For `deposit_30` and `prepaid_only`, stock is reserved **only after a reviewer verifies the required payment**; the Sales Order is then submitted with reservation. For `cod_allowed`, stock is reserved at reseller confirmation. An order that is merely submitted never holds stock. Competing orders cannot reserve the same available stock. The counter cannot sell reserved stock.
3. An order waiting for its deposit expires at the **deposit deadline** (default 24 hours, configurable, OPEN-19). A reserved order cancelled or expired releases its stock. A job does this and logs it. Refunds and changes after reservation need an authorized user.
4. Negative stock is disabled. Out-of-stock items are rejected, with an opt-in restock alert.
5. Phase 0 verifies native reservation behavior (`TASK-P0-04`). If native reservation does not block the counter, use a backend hold table checked at the gateway and never describe it as guaranteed.
6. Warehouses (DEC-49): Main Inventory, Shop (the counter), Gallery, Returns and Defects (not sellable), In Transit. Only warehouses flagged sellable count. Whether Gallery is sellable and which warehouses feed chat availability is OPEN-20 (default: Main Inventory and Shop count for chat; Gallery is display only).

## RULE-COS (cosmetics)
1. Cosmetic items track batch and expiry. Picking follows first-expiry-first-out.
2. Expired batches cannot be sold. A near-expiry report runs at a configurable threshold (default 90 days).
3. Makeup shades are variants; MOQ per family unless overridden.
4. The AI makes no skin, health or safety claims beyond approved product descriptions.

## RULE-RET (DEC-52)
1. Returns use ERPNext return documents and credit notes. Employees may process them within limits; they cannot cancel invoices or issue arbitrary refunds.
2. A return needs a valid original sale (or an approved return reference). The returned quantity cannot exceed the quantity sold minus earlier returns. A reason is mandatory. The employee and times are recorded.
3. Refunds go to the original payment method where feasible. **Manager approval** is required for cash refunds above a configured amount (OPEN-21), returns without a valid reference, and policy exceptions.
4. Returned goods go to the Returns and Defects warehouse and become sellable only after assessment and a transfer.
5. Opened cosmetics: OPEN-04.

## RULE-IDENTITY (DEC-64)
A channel identity (WhatsApp number, Instagram ID, Telegram ID) is linked to a reseller when the reseller messages the shop first from that identity and staff confirm. No paid verification template. Never merge identities by display name.

## RULE-AUDIT
Every price change, discount, override, approval, payment decision, setting change, pause, export and role change is audited with actor, time, old and new values.

## RULE-RULESET
Settings (minimum total, MOQ defaults, tiers, discount limits, payment policies, reservation expiry, handoff thresholds, templates, working hours) are versioned with an effective date. Each order stores the `rule_set_version` it was confirmed under.

## RULE-COST (DEC-45)
Inventory valuation is **FIFO**. Before enabling it in production, audit the site's current valuation setting, stock ledger and opening quantities and values on a staging copy; never switch blindly or edit the ledger by hand; reconcile with the accountant. Opening stock is loaded with real costs.

## RULE-TAX (DEC-26)
The shop charges no VAT and issues no e-invoices. Tax templates stay empty and tax fields are hidden. Revisit if obligations change.

## RULE-PUR (purchasing)
1. You buy from traders in dozens. Buying prices are per dozen.
2. **Local purchases (DEC-31, DEC-47):** goods and supplier invoices arrive together, so use Purchase Invoice with Update Stock. **China imports:** Purchase Order, then one or more Purchase Receipts (ordered, shipped and received quantities, discrepancies), then Purchase Invoice with a Landed Cost Voucher for freight, insurance, customs and clearance; the supplier currency and agreed exchange rate are recorded; advances paid before the invoice are allocated to it; **bank transfer only**. Never double-count stock. For local purchases: Purchase Receipt is not used unless this changes. Stock Entry (Material Receipt) is only for opening stock and non-purchase stock, because it creates no supplier payable. Never create two stock movements for one delivery.
3. Supplier invoice numbers are checked for uniqueness per supplier (Accounts Settings option).
4. Supplier payables come only from the general ledger. No custom debt ledger.
5. Landed costs are recorded when they exist so margin reports use real cost.

## RULE-ACCT (accounting and payments)
1. Customer and supplier balances come from ERPNext's general ledger, never from a custom counter.
2. An invoice is paid only through a recorded payment (Payment Entry or POS payment). Never mark paid without it.
3. Modes of Payment (DEC-48): Cash, Bank Transfer, Vodafone Cash, InstaPay, ECash, WePay, each mapped to its own account (OPEN-10). Rename the legacy E-Wallet mode to Vodafone Cash and add Bank Transfer.
4. Expenses are recorded through standard Payment Entry or Journal Entry with an expense account, by authorized roles only. Sales revenue, cash received and expenses are reported separately.
5. Submitted documents are never deleted. Corrections use returns, credit notes or cancellation with permission.
6. Fiscal years, valuation method and company defaults are not changed casually; assess impact on existing transactions first.


---

# 05 State Machines

Order, payment and shipment are separate state machines. Every transition is idempotent, logged with actor and timestamp, and rejected if illegal. Code lives in `cloud-api` with a transition guard that consults the matrix below.

## Order
`draft → validated → awaiting_shipping_quote → awaiting_confirmation → awaiting_deposit → confirmed → ready_for_dispatch → completed`, with `cancelled` and `expired` as exits. `awaiting_deposit` is skipped for `cod_allowed`.
- `validated`: rules engine passed.
- `awaiting_shipping_quote`: staff must set the fee (RULE-SHIP).
- `awaiting_confirmation`: final total sent; reseller must confirm.
- `awaiting_deposit`: the policy requires a deposit or prepayment that is not yet verified. **No stock is reserved.** Expires at the deposit deadline.
- `confirmed`: required payment verified (or COD policy); ERPNext Sales Order submitted with stock reservation.
- `ready_for_dispatch`: packed and scanned; Delivery Note and Sales Invoice created; the deposit advance is allocated to the invoice (DEC-46).
- `completed`: shipment delivered and balance zero (verified paid or COD remitted). A defect after completion uses the return flow with a credit note; orders are never reopened.
- `expired`: unpaid reservation window elapsed.

## Payment
`unpaid → proof_received → partially_paid → paid`; COD: `cod_pending → cod_collected → cod_remitted`; refunds: `refund_pending → partially_refunded → refunded`; `reconciliation_required` as an exception state.
- Only a `payment_reviewer` can move to `partially_paid` or `paid`.

## Shipment
`not_created → created → picked_up → in_transit → out_for_delivery → delivered`; failures: `delivery_failed → return_in_progress → returned`; `cancelled`; `reconciliation_required`.
- Creating a shipment requires order `confirmed` and (payment `paid`, or deposit met, or COD allowed) and all pack lines scanned (warning mode first, blocking later).

## Cross-state matrix
| Event | Order | Payment | Shipment |
|---|---|---|---|
| Reseller confirms (deposit policy) | awaiting_deposit | unpaid or proof_received | not_created |
| Reseller confirms (COD policy) | confirmed (reserved) | unpaid | not_created |
| Deposit verified | confirmed (reserved) | partially_paid | not_created |
| Packed and scanned | ready_for_dispatch | partially_paid or paid | not_created |
| Ready to ship | confirmed | paid, deposit met, or COD allowed | created |
| COD delivered | completed after remittance | cod_collected then cod_remitted | delivered |
| Delivery failed | confirmed | unchanged (COD back to cod_pending) | delivery_failed, return_in_progress, returned |
| Returned, prepaid | cancelled after stock returned in ERPNext | refund_pending then refunded | returned |
| Cancel before shipping | cancelled | refund_pending if anything was paid | not_created or cancelled |
| Deposit deadline passes | expired | unpaid | not_created |

## Counter hold (POSNext drafts, DEC-29)
`held → resumed → completed`, or `abandoned` after expiry (default 12 hours, configurable). A held sale is a POSNext draft invoice created through POSNext's draft flow. `docstatus = 0` alone never defines a held sale. Resuming a draft updates that same draft and never creates a second invoice. A resumed draft locks to the cashier to prevent concurrent edits.

## Shift (POSNext opening and closing entries)
`open → closing → closed`, with `variance_flagged` when counted cash differs from expected per payment mode. Opening records the float; closing records counts per mode and consolidates through the chosen POS path.

## Store link (cloud-api)
`store_online ⇄ store_offline` per `02-architecture.md` section 4.

## Conversation ownership
`ai ⇄ human`. Chatwoot assignee and status are the source of truth, mirrored by webhook with a version. The cloud re-reads ownership immediately before every AI send and discards the reply if a human took over.


---

# 05a ERPNext Configuration Baseline (Phase E)

ERPNext is simplified by **configuration, not code**. This file is the specification for `TASK-E-01` to `TASK-E-11` and `TASK-E-15` to `TASK-E-17`.

## 1. Principles
- Keep ERPNext's standard stock, accounting, payment and reporting behavior. Simplify the interface around it.
- Allowed: module and workspace visibility, blocked modules per role, Customize Form and Property Setters (hide, default, read-only, mandatory where safe), Role Permission Manager, User Permissions, Print Format Builder, price lists, payment terms, naming series, Stock, Accounts and Selling settings.
- Forbidden: custom Frappe app, Server Scripts, Client Scripts, custom fields, editing core, uninstalling apps (DEC-04).
- Hiding a field never deletes data or removes a process. A hidden field may still be filled by defaults; test it.
- **Never hide without a dependency review:** document identity and status; quantities and units; rates and amounts; required accounting dates; company and currency; tax data; warehouse and stock fields; payment and outstanding amounts; fields required by validation; fields used by an installed app.
- Everything is applied by the idempotent script `infra/erpnext-config/apply.py` through the REST API. Settings live in git as files. The script prints a diff, runs on staging first, and is rerun after every ERPNext upgrade.

## 2. Field and module decision register
Classify every reviewed field and feature as **KEEP, MODIFY, HIDE, OPTIONAL, DEFAULT, DISABLE, INVESTIGATE, DO NOT CHANGE or FUTURE**. Produce `docs/erp-field-register.csv` from the **live site** (never from memory or guesses) with: module and DocType, section, label, verified fieldname, type, current visibility and default, classification, reason, dependencies, method, test case, rollback. Do not invent fieldnames. Mark anything unverified as INVESTIGATE.

## 3. Modules
| Module | Decision | Notes |
|---|---|---|
| Accounting, Stock, Selling, Buying | KEEP | Core |
| Setup and system settings | KEEP, owner and manager only | |
| Manufacturing | HIDE | You do not manufacture |
| HR and Payroll | HIDE | Not needed (DEC-24); no payroll in scope |
| Projects, Quality | HIDE | Not used |
| Assets | HIDE unless equipment tracking is wanted | |
| CRM | HIDE | Chat tools replace it; revisit in Phase G |
| Website, E-commerce, Support | HIDE | |
| Education, Healthcare, others | HIDE if present | Inspect installed apps first |
Hide by blocking modules and workspaces per user or role. Never uninstall an app to simplify navigation. Verify each hidden module has no dependency (for example, accounts reports) before hiding.

## 4. Units, items and barcodes (DEC-20)
- **Stock UOM:** Nos (piece). **Dozen:** UOM with conversion 12. **Purchase UOM and Sales UOM:** Dozen. Item prices are per Dozen. Configure Dozen as whole-number so trading quantities are whole dozens. Piece quantities (single defective pieces, counts, adjustments) use Nos.
- **Barcodes (DEC-32):** internal EAN-13 (GS1 in-store prefix 20–29), as the legacy app generates. Keep all existing barcodes. A dozen (pack) barcode has UOM Dozen; a piece barcode has UOM Nos. Supplier EAN codes are extra barcodes. Barcodes are unique.
- **Item Groups (confirm against the real catalog, OPEN-13):** Accessories and Jewelry (hair accessories, jewelry, bags and similar); Makeup and Cosmetics (face, eyes, lips, nails and similar).
- **Cosmetics:** enable batch and expiry; shade variants for makeup. Accessories: no batch or serial unless needed.
- **Item codes (DEC-32):** existing items keep their codes (the internal EAN-13). New items get an internal EAN-13 as item code. Never reuse a code. Arabic and English names carry the meaning.
- **Simplified Item form:** KEEP code, name, group, UOM and conversion, stock item flag, sales and purchase flags, disabled, barcodes, image, short description, reorder level. HIDE manufacturing and BOM, serial, warranty, weight and shipping, commission, website and similar fields. Keep variant fields for cosmetics shades.
- **Valuation is FIFO (DEC-45).** Audit the existing valuation setting and stock ledger on staging first; never switch blindly or edit the ledger; reconcile with the accountant. Disable negative stock.
- Defaults: warehouse, UOM, company, price list.
- **Warehouses (DEC-49):** Main Inventory, Shop (the counter), Gallery, Returns and Defects (not sellable), In Transit. Sellable flags and chat availability follow OPEN-20.

## 5. Price lists
- Default Standard Buying and Standard Selling lists, per dozen. Tier lists for resellers; customer-specific prices through the Customer's default price list or customer Item Price.
- Validity dates where needed. Price changes restricted to manager and owner. Existing drafts keep their price until refreshed; staff are warned.
- Never hard-code prices in code.

## 6. Purchasing (RULE-PUR)
- Supplier master. Employees see: company name, contact person, phone, address; overseas suppliers also country and currency. Managers see payment terms and outstanding payables. A "China" supplier group is bank-transfer-only (enforced by `diva_guard`).
- **China imports (DEC-47):** Purchase Order, partial Purchase Receipts, Landed Cost Voucher for freight, insurance, customs and clearance, foreign currency with the agreed exchange rate, advances allocated to the final invoice. Confirm exchange-difference treatment with the accountant.
- Purchase Invoice keep: supplier, supplier invoice number and date, posting date, items, quantity, UOM, rate, taxes, totals, paid and outstanding, remarks. Hide project, cost center if unused, landed-cost fields unless used.
- Flow (DEC-31): goods and supplier invoices arrive together, so use **Purchase Invoice with Update Stock**. Hide Purchase Receipt from daily navigation. Turn on supplier invoice number uniqueness.
- Supplier payments through Payment Entry with allocation to invoices; supplier statements and payables reports.

## 7. Sales and customers
- Sales Invoice keep: customer, dates, items, quantity (dozens), UOM, rate, amount, discount, taxes, totals, paid and outstanding, warehouse, remarks. Hide shipping, project, commission, sales-partner and campaign fields if unused.
- Customer: employees see shop name, contact person, phone and address (the preferred courier lives on the reseller profile, not in ERPNext). Managers also see default price list, payment terms, credit limit and outstanding. One record per real customer (never one per invoice). A generic Cash Customer is used only for anonymous counter sales and never overwrites a deliberate selection.
- Discounts use ERPNext fields. Limits per role per RULE-DISC (enforced by local-api; Phase E sets the ERPNext role permission baseline).
- Returns use standard return and credit-note documents; never delete submitted documents.

## 8. Payments, accounts, expenses
- Modes of Payment (DEC-48): Cash, Bank Transfer, Vodafone Cash, InstaPay, ECash, WePay, each with its own account (OPEN-10). Rename the legacy E-Wallet mode to Vodafone Cash and add Bank Transfer.
- Payment Entry for customer receipts and supplier payments, with allocation. Journal Entry restricted to authorized roles.
- Expenses: simple flow through Payment Entry or Journal Entry with an expense account; expense categories tailored to the shop; optional receipt attachment.
- Reports: cash inflows, outflows and net movement. Daily cash closing checklist. Sales totals are not cash received.

## 9. Taxes
Not applicable (DEC-26): the shop charges no VAT and issues no e-invoices. Keep tax templates empty and hide tax fields after a dependency check. Test that invoices, returns and reports show no tax lines. Revisit if obligations change.

## 10. Permissions
- Owner: System Manager (only the owner).
- Manager: sales, purchase and stock manager roles, accounts access as needed, price list edit.
- Cashier and employees: sales user and stock user only. Restricted: price lists, large discounts, cancelling submitted documents, Stock Reconciliation, Journal Entry, Chart of Accounts, user management, sensitive reports.
- Each staff member has their own ERPNext user (DEC-09). Test every workflow with real employee accounts, not only Administrator.

## 11. Standard reports (saved filters first)
Daily sales; sales by item and by customer; purchases by supplier; gross profit; stock balance by item and warehouse; low stock; customer receivables; supplier payables; outstanding invoices; payment history; cash and bank movements; expenses; returns and cancellations; near-expiry batches. Custom aggregation (Control Room) must reconcile with the standard reports.

## 12. Printing
Sales invoice A4, 80 mm receipt, payment receipt, customer and supplier statements, built with Print Format Builder. Show business identity, number, date, customer, item names, quantities in dozens, rates, totals, discounts, taxes, payment and outstanding. EGP formatting. Arabic right-to-left fonts verified on the real printers. Hide internal fields. Labels are drawn by Diva Ops (not ERPNext).

## 13. Backup, staging and rollback
Back up before every change set. Apply configuration to staging first. Keep configuration files in git. Rollback means reapplying the previous configuration commit. Run a restore test on a separate environment each quarter.

## 14. Acceptance (Phase E)
1. Create an item; find it by code, name and barcode (dozen and piece).
2. Purchase invoice with several items; receive stock using the chosen flow; verify ledger and valuation.
3. Sales invoice with several items; quantities and rates are per dozen; stock leaves once.
4. Full payment, partial payment (back office), and an outstanding invoice appearing in the receivables report.
5. Pay a supplier; payables update.
6. Return or cancellation; verify stock and accounting.
7. Taxes and accounting entries match the accountant's expectation.
8. Employee account cannot change prices, cancel documents or open restricted modules; hidden modules are not visible.
9. Standard reports agree with Control Room summaries.
10. Restore a backup on a test environment; reapply configuration after a simulated upgrade.
Record expected result, actual result, evidence and pass or fail for each.


---

# 19 Localization: Arabic and English

Every screen, message, printout and document the system produces exists in **Arabic and English**. **Arabic is primary**: it is designed, built and tested first, with right-to-left (RTL) layout. English is a full alternative, not an afterthought (DEC-39).

## 1. Policy
- Language is a per-user setting. Defaults: cashiers, warehouse and accounts staff start in Arabic; owner and manager choose at first login. A language switch is always visible.
- Resellers: the language is detected per conversation, stored as `preferred_language`, and can be switched by the reseller or staff.
- No hard-coded user-facing string anywhere. All text lives in locale files or ERPNext Translation records.

## 2. Surfaces
| Surface | How it is localized | Phase |
|---|---|---|
| ERPNext Desk (kept screens) | Arabic enabled per user with RTL; domain terms and custom labels as Translation records applied by the config script (configuration, not code); untranslated strings found in `E-01` are translated | E |
| POS Next | Arabic UI and RTL verified in `P0-03`; gaps fixed in the patch set (`E-14b`); Arabic item names, scan info card and errors in Arabic | E |
| Diva Ops, Control Room, Mini App | Shared i18n package: i18next with ICU plurals, `dir` and `lang` set on the page, CSS logical properties, mirrored layouts, `ar.json` and `en.json` | E, PUB, M |
| Telegram admin bot | Replies in the user's language; command tokens stay English (`/orders`) with optional Arabic aliases | PUB |
| Customer chat and AI | Reply in the language of the customer's latest message; Egyptian Arabic by default; mixed Arabic and English supported | A |
| WhatsApp templates | Every template exists in `ar` and `en`, approved separately; Arabic primary | PUB, O |
| Receipts, invoices, statements, packing slips | Arabic primary, optional English second line per setting; A4 and 80 mm | E |
| Labels | Arabic name, EAN-13, optional price per dozen; English optional | E |
| Reports and dashboards | Labels and numbers follow the user's language | E, PUB |
| Public posts | Arabic caption first, optional English block per platform; no wholesale price (DEC-10) | PUB |
| Errors, alerts, notifications | Plain-language, in the recipient's language | all |
| SOPs, training, acceptance scripts | Arabic primary with English copies | E |

## 3. Arabic standards
- **Variety:** UI uses clear Modern Standard Arabic with everyday shop words. Customer chat uses Egyptian Arabic. The owner approves the glossary below (OPEN-17).
- **Digits:** Western digits (0–9) by default in both languages, including receipts and barcodes. A user setting can show Arabic-Indic digits (٠–٩). Input fields accept both and normalize to Western (DEC-40, OPEN-16).
- **Currency and dates:** amount then "ج.م" or "EGP" by setting; Gregorian dates, day/month/year; week starts Saturday; time zone Africa/Cairo.
- **Mixed text (bidi):** Arabic names with Latin brands, SKUs or numbers render correctly (`dir="auto"` or isolation). Barcodes, phone numbers and codes are always left-to-right.
- **Fonts:** bundle one Arabic-capable family (for example Noto Sans Arabic, IBM Plex Sans Arabic or Cairo) with a compatible license; no external font CDN at the counter; tested at small sizes on receipts and labels.
- **Plurals:** Arabic has six plural forms; use ICU plural rules, never "add s".
- **Search normalization:** ignore diacritics and tatweel; treat أ إ آ as ا; ى as ي; ة as ه (search only); convert Arabic-Indic digits to Western; search both Arabic and English names; works on either keyboard layout.
- **Shortcuts on the Arabic keyboard layout:** key shortcuts use physical key codes (for example `KeyF` for Ctrl+F), so they work whichever layout is active.
- **No text baked into images:** labels and posts use real text layers. AI-generated images contain no text.

## 4. Product names (DEC-41)
`item_name` in ERPNext is the **Arabic name** (primary). English name, bilingual descriptions and search keywords live in the `Diva Product Rule` doctype owned by `diva_guard` (fields `name_en`, `description_ar`, `description_en`, `keywords`), so no custom fields are added to ERPNext's Item. Publishing, chat and the AI use these. Suppliers' English or Chinese names can be stored as keywords.

## 5. Thermal and label printing in Arabic (DEC-42)
Many 80 mm thermal printers do not shape Arabic correctly. In `P0-06` print a test sheet (Arabic text, mixed text, digits, EAN-13) on the real printers. Rule: if the printer cannot do it natively, render the receipt and label as a **raster image** (browser print or QZ Tray raster mode) so shaping and direction are correct. Never ship a receipt that prints reversed or disconnected letters.

## 6. Customer language and AI
- Detect Arabic script, English, and **Franco-Arabic** (Arabic typed in Latin letters, for example "3ayez"). Reply in Arabic script unless the customer clearly prefers English.
- Extraction understands Arabic and Egyptian number words ("اتنين دستة", "تلات دست"), Arabic-Indic digits and common spelling variants.
- Product matching uses Arabic synonyms and the keywords above.
- The evaluation set (`TASK-A-03`) includes dialect, Franco-Arabic, spelling variants and noisy voice transcripts.

## 7. Translation process
1. Source keys in English; Arabic written by a native Egyptian speaker (owner or staff), reviewed in context on staging.
2. Glossary locked before `E-14`.
3. Locale changes go through pull requests. CI fails if any key is missing in `ar` or `en`.
4. Pseudo-localization and RTL screenshot tests for key screens in both languages (Playwright).
5. ERPNext translations are stored as Translation records and applied by the config script.

## 8. Initial glossary (owner approves, OPEN-17)
| English | Arabic | English | Arabic |
|---|---|---|---|
| Dozen | دستة | Piece | قطعة |
| Item | صنف | Barcode | باركود |
| Sales invoice | فاتورة بيع | Purchase invoice | فاتورة شراء |
| Return | مرتجع | Discount | خصم |
| Payment | سداد | Cash | نقدي |
| Bank transfer | تحويل بنكي | Vodafone Cash | فودافون كاش |
| InstaPay | إنستا باي | Customer | عميل |
| Supplier | مورد | Cashier | كاشير |
| Shift | وردية | Stock | مخزون |
| Warehouse | مخزن | Balance | رصيد |
| Outstanding | متبقي | Receipt | إيصال |
| Label | ملصق | Hold sale | تعليق الفاتورة |
| Resume | استئناف | New sale | فاتورة جديدة |
| Manager PIN | رقم المدير السري | Minimum quantity | الحد الأدنى للكمية |

## 9. Tasks (effort about 90 h; range 70–120 h)
| ID | Task | Phase | AC |
|---|---|---|---|
| I18N-01 | Glossary draft, font choice, Arabic printer test sheet | P0 | Glossary reviewed; printers tested (`P0-06`) |
| I18N-02 | ERPNext Arabic baseline: enable for staff, find untranslated strings, Translation records via config script | E | Staff roles see RTL Arabic on every kept screen |
| I18N-03 | Arabic print formats (invoice A4, receipt, statements, payment receipt) | E | Print correctly on real printers |
| I18N-04 | Arabic receipt and label rendering decision and implementation (native or raster) | E | `TEST-68`, `TEST-77` pass |
| I18N-05 | POS Next Arabic and RTL fixes; shortcuts by physical key code; Arabic scan info card | E | `TEST-67`, `TEST-71` pass |
| I18N-06 | Shared i18n package for Ops, Control Room, Mini App; locale CI check | E, PUB | `TEST-73`, `TEST-74` pass |
| I18N-07 | Search normalization service (Arabic variants, digits) in `local-api` and cloud | E | `TEST-69`, `TEST-70` pass |
| I18N-08 | Bilingual product info in `Diva Product Rule` | E | Arabic name primary; English fields editable in Ops |
| I18N-09 | Bilingual publishing captions and WhatsApp template languages | PUB | `TEST-75` passes |
| I18N-10 | Customer language detection, Franco-Arabic, number words, reply language | A | `TEST-76` passes |
| I18N-11 | Arabic SOPs and acceptance scripts with Arabic-UI screenshots | E | Staff complete SOPs in Arabic |

## 10. Tests
`TEST-67` to `TEST-78` in `10-quality-security.md`.


---

# 06 Core Modules

Each module lists purpose, interfaces, behavior and acceptance criteria (AC).

## M-GATEWAY (`apps/local-api`, `packages/erpnext-adapter`)
**Purpose:** the only code that talks to ERPNext; the cloud's safe door to the store.
- Typed ERPNext adapter using documented REST resources and whitelisted methods only. Retries with backoff. Reconcile-before-retry using `po_no`.
- Gateway endpoints per `02-architecture.md` section 3, with idempotency keys, request IDs, structured errors.
- Single writer per `external_ref` (unique constraint plus per-key lock).
- Per-user ERPNext API credentials held encrypted (DEC-09). Fallback integration user with actor in remarks.
- Totals, taxes and rounding always from ERPNext responses.
- Contract test suite against staging ERPNext: nightly and before every ERPNext upgrade; failure blocks the upgrade.
**AC:** duplicate `POST /gateway/orders` with the same key returns the same Sales Order; a simulated ERPNext timeout after a successful create results in exactly one Sales Order; unauthenticated calls are rejected.

## M-CATALOG-SYNC
**Purpose:** keep the cloud cache current.
- Change feed with cursor from local-api; nightly full reconcile; drift report.
- Replicates items, barcodes, UOM, pack, batch/expiry flags, prices, stock by sellable warehouse, customers, `product_rules`.
**AC:** a product edited in ERPNext appears in the cloud cache within 60 seconds; reconcile reports zero drift on a clean run.

## M-RULES (`packages/rules-engine`)
**Purpose:** all rules in `04-business-rules.md`.
- Pure functions, no I/O, Decimal money, 100% branch coverage on rule modules.
- Inputs: cart or sale, price/stock facts, settings version, actor role. Outputs: validation result or structured errors, suggested basket additions.
**AC:** TEST-01 to TEST-12 in `10-quality-security.md` pass.

## M-ORDER (`apps/cloud-api`)
**Purpose:** chat and Mini App order lifecycle.
- Cart and draft API; staff order entry (SKU or scanned barcode) through the same API.
- State machines and transition guard (`05-state-machines.md`).
- Flow: draft → validate (rules + gateway availability and prices) → shipping quote by staff → final total to reseller → reseller confirms → if the policy needs a deposit, state `awaiting_deposit` (no stock held) → reviewer verifies the deposit → gateway submits the Sales Order with reservation → packing → `ready_for_dispatch` creates the Delivery Note and Sales Invoice and allocates the deposit advance.
- Reservation expiry job. Price snapshot at confirmation.
- Store-link circuit breaker blocks creation when `store_offline`.
**AC:** a 2,999 EGP chat basket is rejected with the gap; 3,000 passes; counter 2,999 sale is allowed; expired reservation releases stock; link-down state prevents new orders and shows the notice.

## M-PAYMENT
**Purpose:** proofs, human verification, ledger, draft Payment Entry.
- Proof intake (staff upload first, channel media later). Flags for mismatch, reused reference, duplicate hash.
- Verification action restricted to `payment_reviewer`; MFA required.
- Append-only ledger; refund entries; COD events from Bosta.
- Gateway creates a draft Payment Entry after verification, as a **customer advance against the Sales Order** for deposits; accounts submits it in Ops; the advance is allocated to the Sales Invoice at ready-for-dispatch. For suppliers in the China group, a guard rule rejects any mode except Bank Transfer.
**AC:** a customer message saying payment is done never changes payment state; verification writes ledger and draft Payment Entry exactly once on repeat calls.

## M-BOSTA
**Purpose:** shipping.
- Client for create delivery (COD amount), track, cancel, AWB, returns/exchanges. Staging environment in dev.
- Address normalizer to city/zone/district IDs with a confirmation step.
- Webhook receiver: verify secret, deduplicate, map to shipment states, notify the reseller.
- COD remittance reconciliation.
**AC:** duplicate Bosta webhooks send one notification; shipment creation is blocked until order and payment preconditions pass; address without resolved IDs cannot ship.

## M-NOTIFY
**Purpose:** outbound messages.
- Outbox consumer, template registry (WhatsApp approved templates), 24-hour window awareness, rate limits, dead-letter queue.
- Marketing messages only to opted-in resellers with a stored consent record.
**AC:** a message outside the window uses a template or is held for a human; failures retry with backoff, then dead-letter and alert.

## M-SETTINGS
**Purpose:** versioned configuration (RULE-RULESET) with UI in Control Room and replication to local-api.
**AC:** changing the minimum total creates a new version with an effective date; existing orders keep their recorded version.

## M-AUTH-AUDIT
**Purpose:** login, roles, MFA, audit.
- Email + password with MFA for owner and `payment_reviewer`. Role checks on the server. CSRF protection on session endpoints.
- Audit log for every sensitive action (RULE-AUDIT), searchable in Control Room.
**AC:** a cashier cannot approve a discount above 5% or open payment verification; every override appears in the audit log.


---

# 07 Front-End Applications

All front ends are React + TypeScript PWAs sharing `packages/ui`, `auth`, `i18n` and `api-client`. Arabic RTL first with a full English alternative (DEC-11, DEC-39; specification in `19`), light and dark themes, touch targets at least 44 px, plain-language errors.

**Rollout note (DEC-03):** in Phase E, staff first work in the simplified ERPNext Desk configured per `05a-erp-configuration.md` (purchasing, suppliers, expenses, reports, back-office invoices). The Ops screens below are built in slices where Desk is too slow or lacks a needed control (scanning, labels, POS, packing). Do not rebuild a Desk screen that works.

## Role matrix
| Action | owner | manager | cashier | warehouse | accounts | payment_reviewer | sales |
|---|---|---|---|---|---|---|---|
| Counter sale | ✔ | ✔ | ✔ | | | | |
| Discount above 5% | PIN | PIN | | | | | |
| Receive, transfer, count | ✔ | ✔ | | ✔ | | | |
| Submit Payment Entry | ✔ | | | | ✔ | | |
| Verify payment proof | ✔ | | | | | ✔ | |
| Approve resellers, tiers | ✔ | ✔ | | | | | |
| Create shipment | ✔ | ✔ | | ✔ | | | ✔ |
| Settings, pause AI | ✔ | | | | | | |
| Reports, audit log | ✔ | ✔ | | | | | |

## M-OPS (`apps/ops-pwa`, served by local-api)
Task-based screens; home depends on role. Never calls ERPNext directly.
| Screen | Function | ERPNext document |
|---|---|---|
| Items | Barcodes, pack barcode (UOM), product rules, shade variants, duplicate check | Item, Item Barcode |
| Labels | Pick items and copies, preview, print EAN-13 labels (dozen and piece) drawn by the app (no ERPNext print format) | none |
| Receive | Supplier purchase (local): scan or pick items, supplier invoice number and date, rates per dozen, receiving warehouse, extra charges, ordered versus received quantity and discrepancies, payment method, amount and reference linked to the invoice; batch and expiry for cosmetics | **Purchase Invoice with Update Stock** (Stock Entry only for opening and non-purchase stock) |
| Invoices | Sales Invoices, Purchase Invoices, payment receipts, statements: Print, Download PDF, Open in WhatsApp, Send via WhatsApp, send status (`22`) | Sales Invoice, Purchase Invoice, Payment Entry |
| Import purchase | China orders: purchase order, partial receipts and discrepancies, landed costs (freight, insurance, customs), foreign currency, advances, bank-only payments | Purchase Order, Purchase Receipt, Landed Cost Voucher, Purchase Invoice, Payment Entry (simplified Desk first; an Ops screen only if Desk proves too slow) |
| Transfer | From and to warehouse, two-step via In Transit | Stock Entry (Material Transfer) |
| Count | Barcode cycle counts and opening stock | Stock Reconciliation |
| Invoice (back office) | Manager-created invoices with payment terms or installments for approved resellers | Sales Invoice, Payment Terms |
| Collect | Due today, overdue, customer statement, allocate a payment | Payment Entry, Receivable report |
| Payments to post | Draft Payment Entries from verified proofs | Payment Entry |
| Pack | Scan lines of the Delivery Note at ready-for-dispatch; the Sales Invoice is then created with the deposit advance allocated | Delivery Note, Sales Invoice |
**UX rules:** the scan field is always focused; camera scanning on phones; sound or vibration per scan; repeat scan raises quantity; unknown or wrong item shows a large red message and adds nothing; stale-response guard so a late async response never overwrites a later choice; every stock or payment action shows a summary first and offers undo or cancel; scans continue through brief connection drops and sync later, but stock and payment postings need a live connection.

## M-POS (counter: POSNext + `diva_guard`, DEC-29)
**Decision (DEC-29, DEC-34):** the counter uses **POS Next by BrainWise** (`pos_next`; open source, AGPL-3.0, Vue 3, offline-capable, ERPNext 15 and later; see `14` for the name warning, risks and feature decisions) configured through POS Profile, plus the minimal `diva_guard` app and a small POSNext patch set. Plan: (1) configure POSNext with no code; (2) put every business rule in `diva_guard` server hooks so the UI cannot bypass them; (3) patch POSNext only for UI gaps (MOQ message, manager-PIN dialog, dozen display, Arabic labels), kept as a rebasable patch set and offered upstream where possible. AGPL: keep the fork's source available to its users. `TASK-P0-03` is a fit test to confirm v16 compatibility, offline behavior, reservation awareness and the hook points; if it fails, fall back to building a POS mode in Diva Ops.

**POS-CHECK (acceptance for either path):**
1. Barcode scan with multiple barcodes and UOM; repeated scans raise quantity.
2. MOQ and step enforced at the counter (RULE-MOQ).
3. Customer switching; the default customer never overwrites a deliberate choice.
4. Customer-specific price lists; last price sold shown.
5. Discount up to 5% for cashier; above needs manager PIN, audited.
6. Full payment only: cash or non-cash modes (DEC-14).
7. Hold and resume through POSNext drafts; resuming updates the same draft; held sales are never identified by `docstatus = 0` alone.
8. Thermal receipt (80 mm) and A4; printing never resubmits; auto-print is a setting.
9. Shift open and close with per-mode reconciliation and variance flag.
10. Returns and exchanges with credit note and Returns warehouse.
11. Cosmetics: batch selection FEFO, expired blocked.
12. Cannot consume stock reserved for chat orders (RULE-STOCK).
13. Keyboard-only operation on the real keyboard with the owner's current key map (F1 help, F2 customer, F3 quantity, F4 discount, F5 note, F6 delete line, F7 held sales, F8 payment, F9 print, F10 new sale, Ctrl+F search, Ctrl+Delete clear, Ctrl+Z undo, Ctrl+R return), run in a standalone window with `preventDefault`; configurable; a fallback key for any key a browser or OS blocks.
14. Arabic RTL and English switch.
15. Works with no internet while the store LAN is up.
16. No ERPNext core modification and no custom code inside ERPNext.
17. Performance: UI actions under 100 ms, search and barcode under 500 ms, invoices of hundreds of lines usable.
18. **Scan info card:** every scan shows item name, item code, price per dozen and stock, and the quantity added, then returns focus to the barcode field.
19. `qty*barcode` multiplier scan adds that quantity in one scan.
**Safety rules:** never show success before the server confirms; after an uncertain submit read the server state before retry; lock actions on click and use an idempotency key per sale; submitted invoices are never edited in place; unsaved work survives refresh.

## M-CONTROL-ROOM (`apps/control-room`, cloud)
Pages by phase: Overview (needs-attention queue first); Orders (filters by status, date, reseller, city, product; order detail with rule results, proofs, ERPNext and Bosta links, timeline; staff order entry; shipping quote); Payment proofs; Resellers; Inbox context panel; Content queue; Broadcast (one-click send with cost preview, free channels first; `22`); Shipments; Settings; Audit log; AI monitoring (handoff rate, guardrail blocks, kill switch); Media review; Market; System health (link state, queues, failed jobs with safe retry); Sales and stock (today's gross, returns, net, by mode, by cashier, top products, low stock, expiry, receivables, exceptions). Server-side aggregation only. Live updates through server-sent events.
**AC:** a verified proof appears in Ops under Payments to post; the link banner appears within one minute of an outage.

## M-TELEGRAM-ADMIN (`apps/cloud-api`)
Role-based commands: `/orders` with filters (`status=`, `date=`, `reseller=`, `city=`, `product=`, `min=`), `/order <id>`, `/proofs`, `/resellers`, `/ship <id>`, `/neworder`, `/due`, `/stock`, `/brief`, `/pause`, `/resume`, `/post` (Phase PUB), `/prices` (Phase G). Inline buttons. Owner alerts: link state, large discounts, overrides, cash variance, deleted lines, failed jobs. One process owns incoming Telegram updates (webhook mode).

## M-MINI-APP (`apps/mini-app`, Phase M)
Verify `initData` server-side. Approved resellers only for prices. Catalog, search, SKU quick-add, MOQ-aware cart with progress to the 3,000 EGP minimum, basket-gap suggestions, checkout with address picker, reorder, tracking, support button into Chatwoot. Prices always revalidated on the server.


---

# 08 Channels, AI, Media, Content

## M-HUB (Chatwoot, cloud)
- Chatwoot owns channel connections for **WhatsApp, Instagram, Facebook Messenger** at launch (DEC-15). TikTok DM comes in Phase G through an approved partner.
- Backend receives Chatwoot webhooks (verify Chatwoot's secret), replies through the Chatwoot API and fetches attachments through it.
- Ownership truth: Chatwoot assignee and status, mirrored with a version; re-read before every AI send.
- WhatsApp is already on the WhatsApp Business API (DEC-16). `TASK-P0-07` identifies the current provider, tests Chatwoot compatibility, inventories approved templates and plans webhook migration with no message loss. If Chatwoot cannot meet the needs, fall back to Meta webhooks straight into the backend with Chatwoot as UI only.
- Channel rules: WhatsApp free-form replies within 24 hours of the last customer message, otherwise an approved template; Instagram and Messenger 24-hour window (human-agent tag may extend for humans; verify); TikTok DM replies within 48 hours, about 10 messages per window, no business-initiated chats, text and PNG/JPEG only.

## M-AI (`apps/cloud-api`)
**Roles:** understand messages and extract fields; write replies grounded in tool results; sell (basket-gap suggestions, bundles, restock and new-arrival nudges); write captions and enhance images; extract prices from competitor posts.
**Tools (server-side, authenticated):** `search_products`, `get_product`, `get_price(reseller, sku, qty)`, `check_stock`, `get_last_price(customer, sku)`, `get_cart`, `add_to_cart`, `validate_order`, `create_draft_order`, `get_order_status`, `send_price_list`, `find_similar_products(image)`, `record_payment_proof`, `request_human`. **No tool** confirms payment, sets price, applies unauthorized discounts, edits stock or quotes shipping.
**Guardrails:**
1. Every price, stock level, MOQ and total in a reply comes from a tool result in the same turn.
2. Discounts only from configured tier rules.
3. No false scarcity or invented offers.
4. No skin, health or safety claims beyond approved descriptions (RULE-COS).
5. Order data is collected by a slot-filling state machine in code. The model does not remember progress. Phones are strings normalized to `01XXXXXXXXX`, validated by `^01[0125]\d{8}$`.
6. Handoff on: reseller asks for a human, complaint, payment dispute, discount beyond limit, order value above threshold, two consecutive misunderstandings, unsupported content, shipping fee question.
7. Meta and Chatwoot webhooks are deduplicated by message ID. Stale replies are discarded after a human takeover.
8. `store_offline` makes the AI send the ordering-paused notice and create nothing.
9. Reply in the reseller's language (Egyptian Arabic default; Franco-Arabic input is answered in Arabic script); understand Arabic number words and digits; be transparent that replies are automated where required. See `19`.
**Rollout (DEC-17):** offline evaluation on replayed anonymized chats → shadow mode (drafts nobody sees) → staff-assisted drafts → limited auto-replies for low-risk intents → expansion with a kill switch per channel. No stage advances without passing its gate.
**RAG:** approved policies and FAQ; anonymized past chats for tone and objection handling (phones, addresses, names removed); product facts from catalog tables, never price or stock from embeddings.
**Evaluation:** a 100-conversation anonymized test set run on every prompt or model change; metrics: rule correctness, handoff correctness, zero invented facts, zero guardrail breaches.

## M-MEDIA
- Inbound pipeline: record the message first, then an async job downloads media with the channel token, validates type and size, strips EXIF, hashes (SHA-256), stores privately, then processes.
- Voice notes: transcode with ffmpeg, speech-to-text chosen by benchmark on about 50 real Egyptian-Arabic notes (`TASK-P0-09`). Quantities, products and totals from voice are read back in text and confirmed before entering a cart. Phone numbers and addresses from voice must be typed or confirmed digit by digit. Notes over about 2 minutes are summarized and confirmed. Replies are text. Staff voice notes can dictate commands, with a confirm card before any action.
- Images: product photos matched against the catalog (vision plus similarity; add embeddings only if top-3 accuracy falls short); payment screenshots pre-fill a proof via OCR and are flagged for mismatch, reused references and duplicate hashes, never confirmed; defect photos attach to return claims; location pins suggest a Bosta zone for confirmation.
- Text inside images or voice is data, never an instruction.
- TikTok voice is unsupported: reply asking the reseller to type or use WhatsApp.
- Retention: voice 90 days; payment proofs and return photos per accounting retention; signed expiring URLs; scrub personal data before RAG; no use of media for model training.

## M-CONTENT (Phase PUB)
- Flow: product in ERPNext (or photo and name to the Telegram bot) → AI caption and image enhancement (real photo stays the base) → preview with Approve, Regenerate, Edit → publisher posts and stores post IDs, retries safely.
- Targets, in the owner's priority order (DEC-21):
  1. **Facebook Page:** Graph API, pinned version.
  2. **WhatsApp, both ways.** (a) **Broadcast templates** through the existing WhatsApp Business API to opted-in contacts only: approved marketing template, stored consent, segment by category interest, per-message cost preview, monthly budget cap, send queue with rate limits. (b) **Ready-to-post pack** (image, caption, hashtags) delivered to staff for manual posting to the WhatsApp Channel or Status, because WhatsApp Channels have no official posting API.
  3. **Telegram channel:** Bot API.
  4. **Instagram:** Content Publishing API on the Page-linked professional account.
  5. **TikTok:** Content Posting API. Unaudited apps can post only privately, so use upload/draft mode until the audit passes, then direct posting. Start the audit application in Phase 0.
- Publish gate: a product publishes only with barcode, price, MOQ, pack size, images and stock fields (DEC-18). Public posts show no wholesale price.
- Pin the Graph API version; review Meta's changelog each quarter.
**AC:** one approval publishes to all three channels; a failure retries, then alerts; a missing-field product cannot be approved.

## M-MARKET (Phase G)
Telethon worker reads a watch list of public channels at low volume. The LLM extracts product, price, pack, channel, time and image into `price_observations`. Matches to your SKUs are proposed and confirmed by a human. Output: weekly "where am I more expensive or cheaper" report. It never changes your prices.

## M-CAMPAIGN (one-click broadcast in PUB-14, details in `22`, extended in Phase G)
Opt-in segments by category interest; WhatsApp marketing templates with documented consent; restock alerts; new-arrival broadcasts; monthly messaging budget cap with alerts.


---

# 22 WhatsApp: Send Invoices, and One-Click Broadcast

## 1. Send invoices and documents by WhatsApp (DEC-58)
Besides printing, staff can send a **Sales Invoice, Purchase Invoice, payment receipt or statement** to the customer or supplier on WhatsApp. Two levels:

**Level 1 (Phase E, free, no cloud needed).** The Ops **Invoices** screen and a POS Next button show **Print**, **Download PDF** and **Open in WhatsApp**. Open in WhatsApp is a `wa.me` link with the normalized number and a ready message in Arabic or English; staff attach the downloaded PDF. It works whenever the store network works and costs nothing.

**Level 2 (Phase PUB, one click).** **Send via WhatsApp** sends the PDF automatically through the WhatsApp Business API.
1. Staff click Send. `local-api` creates the PDF from ERPNext using the Arabic right-to-left print format.
2. The request goes into the local outbox and then to `cloud-api` with an idempotency key (document name, version hash, recipient).
3. `cloud-api` uploads the PDF as WhatsApp media and sends an **approved utility template with a document header**. The PDF is never a public link.
4. Delivery webhooks update the status: queued, sent, delivered, read, failed. Ops and the Control Room show it. A failure shows the Level 1 fallback.
5. If the internet is down, the request waits in the outbox and sends when it returns. Level 1 still works.

**Templates** (category utility; Arabic primary, English second): `invoice_ready` (customer name, invoice number, total, balance due, document), `purchase_invoice_copy` (for suppliers), `payment_receipt`, `statement`. Keep them transactional. Never add offers: Meta may reclassify the template as marketing, which costs about 18 times more.

**Rules**
- Send only to numbers with recorded consent for transactional WhatsApp (captured when the customer or supplier is created or at the first chat). Normalize the phone number.
- One send per document version; a resend needs a deliberate click.
- Per-customer setting "send invoice automatically on submit" for repeat resellers (default off).
- Suppliers: send only when they use WhatsApp (China suppliers are usually not required).
- Show the cost estimate in Settings, not on every click.

**Cost (Meta, Egypt, from 1 October 2026):** a utility message is $0.0036 (about 0.19 EGP), possibly plus 14% VAT. 1,000 invoices cost about $3.60. A service reply inside an open 24-hour window is also $0.0036 after the first 1,000 per number each month.

### 1a. Customers message first: the cheapest valid path (DEC-64)
WhatsApp lets you reply to a customer freely, including with a PDF, for 24 hours after **they** message you. Sending after that window needs an approved template. So:
1. **Put a "Message us" link and QR** (`wa.me/<number>?text=...`) on receipts, invoices, statements, the shop sign and your public posts (`ENH-C-09`). A customer who scans it messages the shop first and opens the window.
2. **Choose the path automatically when staff click Send via WhatsApp:** (a) the customer's window is open: send the document as a normal reply (service message; the first 1,000 per number each month are free, then the utility rate); (b) the window is closed and consent exists: send the approved utility template; (c) otherwise show the free manual link from Level 1.
3. **Verify a reseller's phone by their first inbound message** (it proves they control the number), with staff confirmation. No paid verification template is used.
Savings are small for invoices (about $0.0036 each) but this also avoids verification fees and keeps follow-ups inside the window.

## 2. One-click broadcast to all customers (DEC-59)
**Is WhatsApp the cheapest way? No.** A WhatsApp marketing message to Egypt costs **$0.0644** (about 3.4 EGP, possibly plus 14% VAT) with no volume discount, so 500 customers cost about $32 per broadcast. It is the only way to reach every customer reliably in one click, so we build it, but with free options first.

Control Room, **Broadcast** page:
1. Write the message or pick an approved template (Arabic and English).
2. Choose the audience: all opted-in customers, or a segment (category interest, tier, last purchase date).
3. See the recipient count and the **cost**, then confirm.
4. Send. Results show delivered, failed and STOP replies.

**Channels, cheapest first**
| Channel | Cost | Reach |
|---|---|---|
| Telegram channel or bot subscribers | Free | Customers who joined |
| WhatsApp Channel or Status (ready-to-post pack, posted by staff) | Free | Followers only; manual |
| WhatsApp marketing template to opted-in customers | $0.0644 per delivered message | Every opted-in customer |

Default policy: send ordinary offers on the free channels first; use the paid WhatsApp broadcast for important announcements and targeted segments. The monthly spend cap exists but is off for now (DEC-33).

**Opt-in is required.** Meta's rules require opt-in for business-initiated marketing messages. Capture consent at the counter (a checkbox when creating a customer), at the first chat, and by a START keyword. Store proof (who, when, source). Honor STOP immediately. Only opted-in contacts are ever included; the page never offers "everyone" beyond that.

## 3. Data additions
`message_consents` (party, channel, category transactional or marketing, source, time, revoked time); `outbound_documents` (document type and name, version hash, recipient, status, provider message ID); `broadcasts` and `broadcast_recipients` (message, audience, cost estimate, status per recipient).

## 4. Tasks
| ID | Task | Phase |
|---|---|---|
| E-18 | Level 1 invoice sharing: Print, Download PDF, Open in WhatsApp in Ops Invoices and POS Next | E |
| PUB-13 | Level 2 one-click send with utility templates, outbox, status tracking, fallback | PUB |
| PUB-14 | One-click broadcast page with audience, cost preview, confirmation, free channels first, consent and STOP handling | PUB |
Effort about 50–90 h in total.

## 5. Tests
`TEST-92` to `TEST-100` in `10-quality-security.md`.


---

# 14 Feature Decision Matrix and Final ERPNext Stack

This file records what we use from **standard ERPNext**, from **POS Next**, and from the **legacy `diva_store` app**, and what we drop. It is the final answer to "which one do we use for what" (DEC-34).

## 1. Final ERPNext stack
| Layer | Choice |
|---|---|
| Core | Standard ERPNext 16, configured only (`05a`), unneeded modules hidden |
| Counter POS | **POS Next by BrainWise** (`pos_next`, GitHub `BrainWise-DEV/POSNext`), pinned version, plus `diva_guard` and a small patch set |
| Staff screens | **Diva Ops** (React PWA served by `local-api`): Receive, Transfer, Count, Labels, Items, Collect, Pack |
| Management | Control Room dashboard (cloud) |
| Legacy `diva_store` | Retired after POS Next cutover; useful logic ported (section 4) |

**Name warning.** There is a different, older app also called "POSNext" (publisher exvas, listed on the Frappe marketplace for ERPNext 14 and 15, MIT). A marketplace review says uninstalling it leaves custom fields behind and can break a site. **Do not install it.** Install only `pos_next` from `https://github.com/BrainWise-DEV/POSNext` (AGPL-3.0, Vue 3, offline-first).

## 2. POS Next: what it gives us (from its published notes; verify in `TASK-P0-03`)
Offline-first selling with automatic sync (the developer says it holds for about a day or until shift close); barcode and keyboard use; shift management with Sales vs Shifts and Payments and Cash Control reports (with bank deposit information); credit sales with settings to allow or block them; paying a customer's receivable account from the POS; offers and promotional schemes with minimum and maximum discount logic; packed items for Product Bundles; item scope by POS Profile; customer group and territory defaults; invoice list with payment mode; offline receipt handling and printing; extension hooks.
**Risks:** the project is young (about 150 stars); its v1.17.0 release notes include a rollback of a change that hid all records, so upgrades can regress; it adds its own custom fields and permission query conditions to ERPNext (vendor-owned; document them and rehearse uninstall); AGPL means a modified fork's source must be available to its users.
**Rules for using it:** pin the exact version; never auto-upgrade; rehearse every upgrade and an uninstall on staging first; keep our patch set small and rebasable; test offline for a full shift (`TEST-53`).

## 3. Feature decisions
### Counter sales
| Feature | Legacy app | POS Next | Decision |
|---|---|---|---|
| Barcode scan adds a line; repeated scan raises quantity | yes | yes (verify) | **POS Next** |
| `qty*barcode` multiplier (for example `5*890…`) | yes | unknown | **Recommended patch** if missing (fast shelf-picking in dozens) |
| Undo last scan (Ctrl+Z) | yes | unknown | Patch candidate, low priority |
| **Scan info card:** name, code, price per dozen and stock shown on every scan | yes (grid and status bar) | unknown | **Required patch** (E-14b) if POS Next does not already show it |
| Hold and resume | yes, buggy | drafts | **POS Next drafts** |
| Customer picker and card (outstanding, limit) | yes | customer dialog, credit info | **POS Next**; patch the card only if too thin |
| **Keyboard shortcuts** (your current map: F1 help, F2 customer, F3 quantity, F4 discount, F5 note, F6 delete line, F7 held sales, F8 payment, F9 print, F10 new sale, Ctrl+F search, Ctrl+Delete clear, Ctrl+Z undo, Ctrl+R return) | yes | built-in shortcuts (map unverified) | **Required patch:** the POS Next keymap is replaced by your current keys, with `preventDefault` in a standalone window, tested on the real keyboard; configurable, with a fallback if a browser blocks a key |
| Command palette (Ctrl+K) | yes | no | Drop |
| Discounts | unlimited, client-trusted | offers, min/max discount | **POS Next offers + `diva_guard`** (5% cashier limit, PIN above, server-side) |
| Payments (cash, non-cash, split, change) | recorded wrongly | yes | **POS Next**; partial and credit blocked at the counter by setting plus `diva_guard` |
| Shift open and close, reconciliation | legacy shift report | shifts, cash control reports | **POS Next** |
| Receipts 80 mm and 58 mm | print formats | printing and offline receipts | **POS Next**; reuse the legacy layout if its default receipt is weaker |
| Returns (Quick Return Ctrl+R) | yes | verify | **POS Next returns**; fall back to standard ERPNext return |
| Low-stock tint on rows | yes | unknown | Optional patch candidate |
| Today's sales widget | yes | reports | Control Room sales page |
| Offline operation | no | yes | **POS Next** (tested) |
| Product bundles (sets) | no | packed items | **POS Next** (when needed) |
| Send invoice by WhatsApp | deferred | not core | Phase G |
| Price check screen | yes | item search shows price | POS Next search; Ops mini screen only if needed |

### Stock and items
| Feature | Legacy | Decision |
|---|---|---|
| Receiving by scan | Stock Entry Material Receipt (no supplier payable) | **Replace:** Ops Receive using Purchase Invoice with Update Stock (DEC-31) |
| Quick Add Item with EAN-13 generation | yes, unvalidated, `ignore_permissions` | **Port** the generator into `local-api` with validation, permissions and tests; keep existing barcodes |
| Barcode label printing | page | **Rebuild** in Ops Labels (EAN-13, dozen and piece) |
| Low-stock alert report and dashboard | report | Standard stock reports with reorder levels; Control Room page; Telegram alert in Phase PUB |
| Transfers and counts | none | Ops (new) |

### Finance and reports
| Feature | Legacy | Decision |
|---|---|---|
| Collect payment with FIFO allocation | page, `ignore_permissions`, no idempotency | **POS Next** pay-on-receivable at the counter; **Ops Collect** for the back office, porting the FIFO idea with permission checks, idempotency and reference fields |
| Customer statement | page | Standard Statement of Account and General Ledger; Ops Collect view; WhatsApp send in Phase G |
| Sales summary, top items, top customers | reports | Standard reports plus Control Room (must reconcile with standard) |
| Profit report (cost from stock ledger) | report | Control Room query, reconciled to standard gross profit |
| Dashboard | Desk page | Control Room |
| Daily server backup script and cron | script | **Reuse the idea** in E-17 with off-site copy and restore test |
| Telegram stock alerts and daily report (backlog) | not built | Phase PUB and Phase G |
| Overdue customer alerts (backlog) | not built | Phase G |

### Dropped
Desk-injected POS (22 JS modules), the CSS that hides Desk elements, the Diva Sale pilot, `Diva POS Settings`, duplicate and `*_old` files, committed build artifacts and the zip inside the package.

## 4. Net effect on the plan
- Counter work shrinks to configure, guard, patch and cut over (`E-14` to `E-14d`).
- We keep our own Receive, Labels, Items, Collect, Transfer, Count and Pack screens because neither app provides them correctly.
- `diva_guard` stays small: server hooks and its own doctypes only.
- Open item: `TASK-P0-03` must answer every "verify" and "unknown" cell above before `E-14` starts.


---

# 09 Build Plan

Order (DEC-03): **P0 → E → PUB → O → B → C → A → M → G**. There are no fixed dates (DEC-23). Each phase ends at an exit gate; the next phase starts only when the gate passes. Effort is an estimate for one developer working with an AI coding agent, in hours.

| Phase | Name | Effort (h) |
|---|---|---|
| P0 | Foundations and decisions | 35–55 |
| E | ERPNext: simplify, operate, POS | 370–620 |
| PUB | Publishing to Facebook, WhatsApp, Telegram, Instagram, TikTok | 180–300 |
| O | Chat orders engine | 150–230 |
| B | Bosta shipping and reports | 70–110 |
| C | Chat hub, human-first | 60–100 |
| A | AI agent with voice and images | 200–300 |
| M | Telegram Mini App | 110–160 |
| G | Growth | later |
| | **Total P0 to M** | **about 1,175–1,875** |

Task rule: every task has acceptance criteria (AC) and dependencies (Dep). A task is done only when AGENTS.md's Definition of Done is met.

## Phase P0 — Foundations and decisions
| ID | Task | Dep | AC |
|---|---|---|---|
| P0-01 | Rotate every exposed credential (Telegram bot token, Meta tokens, URL-shortener token, webhook verify token); move to secret stores | none | Old credentials revoked; secret scan clean; nothing in workflow JSON |
| P0-02 | Disable or authenticate the legacy "Nanobot" webhooks | none | Unauthenticated calls return 401 or endpoints are gone |
| P0-03 | **POS Next fit test (2–3 days):** install BrainWise `pos_next` (not the exvas "POSNext") on staging with a copy of production data; run POS-CHECK in `07`; answer every "verify" and "unknown" cell in `14` including Arabic completeness, RTL, Arabic keyboard layout and Arabic receipt printing (ERPNext 16 compatibility, full-shift offline test, reserved-stock behavior, hook points for `diva_guard`, receipt printing and QZ Tray, Arabic RTL, `qty*barcode` multiplier, UOM Dozen and Nos handling, returns, customer card, uninstall rehearsal) | P0-04 | Scored written result and a go or no-go DEC; if no-go, build a POS mode in Diva Ops |
| P0-04a | **Install a disposable dev ERPNext 16** with `scripts/start-dev-erpnext.sh` (frappe_docker `pwd.yml`; pin the image tag to version 16 if it is not already) and record the versions | P0-10 | ERPNext answers on port 8080; versions recorded in `docs/appendix-erpnext-verification.md` |
| P0-04 | Verify ERPNext on staging: version, installed apps, stock reservation behavior, Item Barcode with UOM, Dozen whole-number UOM, Payment Terms, credit limit, the REST endpoints the adapter needs | P0-04a | Findings file in `docs/appendix-erpnext-verification.md` |
| P0-05 | Measure infrastructure: store VM capacity, internet uptime and latency to the chosen cloud region, WireGuard feasibility, UPS | none | Numbers recorded; cloud provider chosen |
| P0-06 | Hardware inventory and test: scanner, thermal receipt printer, label printer; browser print and QZ Tray with Arabic text | none | Models recorded; Arabic receipt and label print correctly |
| P0-07 | WhatsApp: identify current API provider, approved templates, number status; Chatwoot compatibility check; Meta business verification status; Instagram and Facebook Page connection status | none | Report with migration plan for later phase C |
| P0-08 | Accountant check: VAT, e-invoicing obligations, payment-mode account mapping | none | Written answer; OPEN-08, OPEN-10 closed or scheduled |
| P0-09 | Datasets: item master export, 100 anonymized chats, 50 voice notes; ERPNext backup and restore test | none | Datasets stored privately; restore proven on a separate VM |
| P0-10 | Monorepo, CI, Docker Compose (cloud and store), secret scanning, `make` commands | none | `make setup test lint` pass in CI |
| P0-12 | **Only if the legacy site still exists:** verify legacy-app findings on a staging copy (`13`); otherwise skip, because the legacy app is retired anyway: payment recording in Diva Sale invoices, held drafts, bank-type Payment Entry references, API duplicates | none | Results recorded in `13`; severity confirmed |
| P0-11 | Start the TikTok developer app and audit application; check Meta app permissions for Facebook and Instagram publishing | none | Applications submitted; status tracked |
**Exit gate P0:** no exposed secrets; P0-03, P0-04 results recorded; CI green; applications submitted.

## Phase E — ERPNext (first priority)
Spec: `05a-erp-configuration.md`, `07` (Ops and POS), `04` rules.
| ID | Task | Dep | AC |
|---|---|---|---|
| E-00a | **Install ERPNext 16 on the store VM (production)** with the frappe_docker production setup; HTTPS on the LAN; daily backups with an off-site copy; restore test; load items and customers by import, no demo data | P0-04 | ERPNext 16 runs on the store VM; restore test passed |
| E-00 | Legacy `diva_store` retirement plan and salvage (`13`) | P0-12 | Written plan, salvage list, rollback path agreed |
| E-01 | Baseline snapshot of site config; installed-apps inventory; **field register from the live site** | P0-04 | `erp-field-register.csv` complete, every row classified, no invented fieldnames |
| E-02 | Hide unneeded modules and workspaces per role | E-01 | Employee accounts cannot see hidden modules; no broken menus; tests pass |
| E-03 | `infra/erpnext-config/apply.py`: idempotent configuration script with diff report | E-01 | Re-running changes nothing; runs on staging first; reapplied after a simulated upgrade |
| E-04 | Units, items, groups, codes, valuation, negative stock off, cosmetics batch and expiry, simplified Item form | E-03, OPEN-13 | RULE-UOM tests pass: dozen purchase and sale, piece return |
| E-05 | Price lists per dozen, tiers, price-edit permissions | E-04 | Price fetch correct per customer; employee cannot edit price lists |
| E-06 | Barcodes: load dozen and piece barcodes, uniqueness, supplier EAN as extra | E-04 | Duplicate barcode rejected; dozen scan adds 1 dozen |
| E-07 | Warehouses (Main Inventory, Shop, Gallery, Returns and Defects, In Transit); opening stock count and import; FIFO audit on staging (RULE-COST) | E-04 | Stock reconciliation matches the physical count |
| E-08 | Purchasing: suppliers, **Purchase Invoice with Update Stock** (DEC-31), supplier payments, payables | E-04 | Purchase test passes with one stock movement per delivery |
| E-08b | **China import flow:** Purchase Order, partial Purchase Receipts, Landed Cost Voucher, foreign currency, advances, bank-only rule; **Quick local purchase** details (discrepancies, extra charges, payment at purchase) | E-08 | TEST-79 passes: 10 dozen paid 40% then 60% shows correct stock, value, supplier balance and payment history |
| E-09 | Sales, customers, payment modes (six) and account mapping, receivables | E-04, OPEN-10 | Sales, full payment, outstanding invoice and receivable report agree |
| E-10 | Expenses and cash tracking; daily cash closing checklist | E-09 | Cash report reconciles with ledger |
| E-11 | Taxes: confirm none (no VAT, no e-invoice); hide tax fields | E-01 | Invoices show no tax lines |
| E-12 | `local-api` skeleton, `erpnext-adapter` with contract tests, `rules-engine` counter rules (MOQ in dozens, discount limits, override audit) | E-04 | Contract tests pass nightly on staging; rules coverage 100% on branches |
| E-13 | Ops slice 1: Items and barcodes (port the EAN-13 generator), Labels (dozen and piece), Receive (Purchase Invoice), Transfer, Count, Collect | E-06, E-12 | TEST list for Ops passes; label scans back correctly |
| E-14 | **POSNext adoption:** install and configure (POS Profile, shifts, offline, QZ Tray receipts, Arabic), payment modes, cashier roles | E-12, P0-03 | POS-CHECK items 1, 3, 6–11, 13–15 pass |
| E-14a | `diva_guard`: server hooks for MOQ in dozens, discount limits by role with manager PIN, price integrity against the price list, no credit or partial payment at the counter, reserved-stock check; `Diva Product Rule` doctype; imports `rules-engine` | E-12, E-14 | TEST-02 to TEST-06 and TEST-44 to TEST-48 pass; the browser cannot bypass any rule |
| E-14b | POS Next patch set. **Required:** scan info card (name, code, price per dozen, stock), the owner's key map, MOQ message, PIN dialog, dozen display, Arabic labels, invoice-sharing buttons (Print, Download PDF, Open in WhatsApp). **If missing:** `qty*barcode` multiplier, undo last scan, low-stock tint. Rebased on upstream | E-14a | TEST-55 to TEST-57 pass; patches in git with tests; upgrade rehearsal on staging passes |
| E-14c | Cosmetics batch and expiry at the counter (FEFO) | E-14 | TEST-10 passes |
| E-14d | Pilot, cutover and legacy retirement (`13` section 4) | E-14b, E-00 | Legacy app uninstalled after backup; one week without a blocking issue |
| E-15 | Standard reports with saved filters; invoice A4, 80 mm receipt, payment receipt, statements | E-09 | Reports agree with ledger; Arabic prints correctly |
| E-16 | Roles and users: one ERPNext user per staff member; permission matrix; tests with employee accounts | E-02 | Matrix tests pass |
| E-18 | **Invoice sharing, level 1 (free):** Ops Invoices screen and POS Next buttons: Print, Download PDF, Open in WhatsApp (`wa.me` link with the normalized number and a ready Arabic or English message) for Sales Invoices, Purchase Invoices, payment receipts and statements; receipts and invoices also carry a "Message us" QR and link (`22`, ENH-C-09) | E-15, E-13 | TEST-92 passes |
| E-17 | Backups, restore test, downtime runbook, Arabic SOPs, staff training; retire daily Desk clutter | E-14d, E-15, E-16 | Staff complete the full workflow from SOPs; restore test passed |
**Exit gate E:** acceptance list in `05a` section 14 passes; POS-CHECK passes; staff use the new system for daily work for one full week without a blocking issue.

## Phase PUB — Publishing (second priority)
| ID | Task | Dep | AC |
|---|---|---|---|
| PUB-01 | Cloud foundation: `cloud-api`, Postgres, auth with MFA, audit log, object storage, observability, deploy to a small VPS first (2 vCPU, 4 GB; resize when chat and AI start), media and backups on Cloudflare R2 or Backblaze B2, self-hosted Uptime Kuma and GlitchTip | E exit | Health and alerts working; MFA enforced for owner |
| PUB-02 | WireGuard Link, gateway endpoints for health and catalog changes, catalog sync to the cloud cache | PUB-01, E-12 | Item change appears in the cloud cache within 60 seconds; zero drift on reconcile |
| PUB-03 | Telegram admin bot skeleton with roles; owner alerts | PUB-01 | Role checks enforced; alert delivered |
| PUB-04 | Control Room shell: login, roles, content queue, system health | PUB-01 | Pages load from the cloud API |
| PUB-05 | Publish gate: product needs barcode, price, MOQ, pack size, images, stock fields | PUB-02 | Missing-field product cannot be approved |
| PUB-06 | AI caption and image enhancement with preview (Approve, Regenerate, Edit); real photo stays the base | PUB-04 | Nothing publishes without approval; prompts and source photo stored |
| PUB-07 | Facebook Page publishing, pinned Graph API version, retries, post IDs | PUB-06, P0-11 | Post appears; failure retries then alerts |
| PUB-08 | Instagram publishing | PUB-06 | Same as PUB-07 |
| PUB-09 | Telegram channel publishing | PUB-06 | Same |
| PUB-10 | **WhatsApp both ways:** (a) broadcast templates to opted-in contacts with consent records, segments, cost preview, optional budget cap (off by default, DEC-33), rate limits; (b) ready-to-post pack for Channel or Status | PUB-06, P0-07 | Template approved by Meta; no send without consent; optional budget cap works when enabled; pack delivered to staff |
| PUB-11 | TikTok: upload or draft mode now; direct posting after audit | PUB-06, P0-11 | Draft appears; direct post only after audit approval |
| PUB-12 | Publishing report and public-price check | PUB-07 | No public post contains a wholesale price; failure list visible |
| PUB-13 | **Invoice sharing, level 2 (one click):** Send via WhatsApp by the cheapest valid path (free reply inside an open 24-hour window, else approved utility template with document header, else the manual link), local outbox, idempotency, delivery status (`22`) | PUB-02, E-18, P0-07 | TEST-93 to TEST-96 pass; 1,000 sends cost about $3.60 |
| PUB-14 | **One-click broadcast** page: audience, cost preview, confirmation, free channels first, consent and STOP handling (`22`) | PUB-10, PUB-13 | TEST-97 to TEST-100 pass |
**Exit gate PUB:** one approval publishes to Facebook, Instagram and Telegram; WhatsApp broadcast and pack both work; TikTok works to the level the audit allows.

## Phase O — Chat orders engine
| ID | Task | Dep | AC |
|---|---|---|---|
| O-01 | `rules-engine` chat rules: 3,000 EGP minimum, basket-gap suggestions, shipping step, availability | E-12 | TEST rules cases pass |
| O-02 | Cart and draft API; staff order entry (SKU or barcode) in Control Room and Telegram `/neworder` | O-01 | Staff enter a chat order with live rule errors |
| O-03 | Order, payment and shipment state machines with transition guard and audit | O-01 | Matrix tests in `05` pass |
| O-04 | Gateway order create-or-get; reserve only after the required payment is verified; release; deposit-deadline expiry job | O-03, PUB-02 | Duplicate create returns the same order; timeout then retry yields one Sales Order; expiry releases stock |
| O-05 | Shipping quote step (staff sets fee) | O-03 | AI path cannot quote shipping |
| O-06 | Payment proofs, append-only ledger, human verification, draft Payment Entry as customer advance, Payments to post, deposit calculation (30% for new resellers) | O-03 | No automated path verifies payment; repeat verification creates one ledger entry |
| O-07 | Notifications: outbox, templates, 24-hour window, dead-letter queue | O-03 | Dead letters visible; retries with backoff |
| O-08 | Settings with versions and effective dates; replicate to local | PUB-04 | Order keeps its `rule_set_version` |
| O-09 | Link-down circuit breaker and customer notice | PUB-02 | New orders blocked within about 45 s; notice sent; resumes after 3 successes |
| O-10 | Ready-for-dispatch step: Delivery Note then Sales Invoice, allocate deposit advance, reconcile balance | O-04, O-06 | Invoice equals goods plus shipping; advance allocated; remaining balance correct (TEST-85, TEST-86) |
**Exit gate O:** TEST cases O in `10` pass.

## Phase B — Bosta
B-01 client and staging environment, manual courier support (courier, tracking number, fee, status, outcome; preferred courier on the reseller profile); B-02 address normalizer to city, zone, district IDs with confirmation; B-03 shipment creation with preconditions and scan-to-pack warning; B-04 webhook receiver (verify, deduplicate, map states, notify); B-05 returns and exchanges; B-06 COD remittance reconciliation; B-07 manager reports (counter and chat). **AC:** duplicate webhooks send one notification; no shipment without resolved address IDs and met payment preconditions. **Exit gate B:** order traced from draft to delivered in staging.

## Phase C — Chat hub, human-first
C-01 deploy Chatwoot; connect WhatsApp (migrate from the current provider with no message loss), Instagram, Facebook; C-02 durable inbound events and dedup; C-03 ownership and takeover rules with version check; C-04 template management; C-05 inbox context panel in Control Room. **Exit gate C:** staff run all three channels from one inbox for a week; no lost messages.

## Phase A — AI agent
A-01 orchestrator and tools; A-02 guardrails; A-03 evaluation set and replay; A-04 shadow mode; A-05 staff-assisted drafts; A-06 limited auto-replies for low-risk intents; A-07 media (voice, images, proofs) per `08`; A-08 RAG with anonymized chats; A-09 expansion and kill switches; A-10 router for routine intents (price, stock, order status, opening hours) answered by fixed logic and templates before any model is called; A-11 small-model-first with escalation to a bigger model for hard cases, plus prompt caching. **Gates:** each stage passes the evaluation thresholds (rule correctness, handoff correctness, zero invented facts, zero guardrail breaches) before the next begins.

## Phase M — Mini App
M-01 `initData` verification; M-02 catalog and search; M-03 MOQ-aware cart with minimum progress; M-04 checkout, tracking, reorder. **Exit gate M:** a reseller completes an order with no staff retyping.

## Phase G — Growth (later)
Market price monitor, restock and new-arrival campaigns, reseller tiers and credit controls, TikTok DM via partner, analytics, margin and reorder reports, supplier purchasing automation.


## Accepted enhancements (DEC-37)
Accepted items from `16` join these phases. Each is a task with its own acceptance criteria written in `16` and checked at the gate. Effort is in addition to the table above.

| Phase | Accepted enhancements | Effort (h) |
|---|---|---|
| P0 | ENH-R-01, ENH-R-03, ENH-R-04, ENH-S-01, ENH-S-02 | about 30 |
| E | ENH-A-01, ENH-A-02, ENH-A-03, ENH-A-04, ENH-A-05, ENH-A-06, ENH-A-07, ENH-A-10, ENH-C-01, ENH-C-02, ENH-C-03, ENH-C-04, ENH-I-01, ENH-I-05, ENH-I-07, ENH-R-05, ENH-R-06, ENH-R-07, ENH-S-03, ENH-S-09 | about 176 |
| PUB | ENH-M-01, ENH-M-02, ENH-M-03, ENH-M-04, ENH-M-05, ENH-M-06, ENH-M-07, ENH-L-01, ENH-L-02, ENH-L-03, ENH-I-02, ENH-I-04, ENH-K-01, ENH-K-02, ENH-S-04, ENH-S-05, ENH-S-08 | about 186 |
| O | ENH-C-06, ENH-M-08, ENH-S-06 | about 60 |
| C | ENH-H-01, ENH-H-04, ENH-H-05 | about 46 |
| A | ENH-H-02, ENH-H-03, ENH-H-08, ENH-H-10 | about 38 |
| All gates | ENH-R-02 | about 20 |

**With the accepted enhancements the total for P0 to M is about 1,620–2,570 hours** (base 1,175–1,875 plus about 556 h at 80%–125%).

Gate additions: P0 gate also requires ENH-R-01, R-03, R-04, S-01, S-02. Gate E also requires the cutover plan and opening balances signed (ENH-R-05, A-01) and the recovery drill (ENH-S-03). Every gate uses the scripts in `18`.

## Localization tasks (DEC-39)
Tasks `I18N-01` to `I18N-11` in `19` join these phases: P0 (glossary, fonts, printer test), E (ERPNext Arabic, print formats, POS Arabic, search, product names, SOPs), PUB (shared locale package, bilingual publishing and templates), A (customer language handling). Effort about 90 h (70–120 h). **Total for P0 to M including accepted enhancements, localization and the v4.1 additions: about 1,870–3,030 hours.** The v4.1 additions (China imports, deposits and advances, effective-discount and price-conflict rules, stricter returns, manual couriers) are about 90–170 hours. The v5.0 additions (WhatsApp invoice sending and one-click broadcast) are about 50–90 hours.

## Dependencies summary
P0 → E → PUB → O → B → C → A → M. Exceptions: P0-11 runs in parallel with E so audits finish early; the TikTok and Meta permission waits must not block E.


---

# 10 Quality and Security

Record for every test: expected result, actual result, evidence, pass or fail. Never mark a test passed unless it was run.

## 1. Test matrix
| ID | Area | Scenario | Level | Phase |
|---|---|---|---|---|
| TEST-01 | Rules | Chat basket 2,999 EGP rejected with gap 1; 3,000 accepted | unit | O |
| TEST-02 | Rules | Counter sale below 3,000 EGP is allowed | unit | E |
| TEST-03 | Rules | Line below `min_qty` or not a multiple of `qty_step` (in dozens) rejected at counter and in chat | unit | E |
| TEST-04 | Rules | Cashier discount 5% allowed; 5.01% requires PIN; audit row written | unit | E |
| TEST-05 | Rules | Counter payment must be full; partial or credit is rejected | unit | E |
| TEST-06 | Rules | Price source order: customer list, tier list, standard | unit | E |
| TEST-07 | Rules | Price changed during checkout triggers reconfirmation | integration | O |
| TEST-08 | Rules | Reserved stock cannot be sold at the counter | integration | O |
| TEST-09 | Rules | Unpaid reservation expires after 24 h and releases stock | integration | O |
| TEST-10 | Rules | Expired cosmetics batch cannot be sold; FEFO picks earliest expiry | integration | E |
| TEST-11 | Units | Buy and sell in dozens; return 2 pieces posts 2 Nos; stock ledger in pieces | integration | E |
| TEST-12 | Units | Dozen barcode adds 1 dozen; piece barcode adds 1 piece | integration | E |
| TEST-13 | ERP | Create item; find by code, name, barcode | e2e | E |
| TEST-14 | ERP | Purchase with several items; one stock movement per delivery | integration | E |
| TEST-15 | ERP | Sales with several items; stock leaves once | integration | E |
| TEST-16 | ERP | Partial payment (back office) and outstanding appear in receivables | integration | E |
| TEST-17 | ERP | Supplier payment updates payables | integration | E |
| TEST-18 | ERP | Return and cancellation correct stock and accounts | integration | E |
| TEST-19 | ERP | Employee account cannot edit prices, cancel documents or open hidden modules | manual | E |
| TEST-20 | ERP | Configuration script is idempotent and reapplies after a simulated upgrade | integration | E |
| TEST-21 | ERP | Backup restores on a separate environment | manual | E |
| TEST-22 | Counter | 18-step cashier script (scan, repeat scan, qty, customer, discount, note, delete, hold, resume, cash, non-cash, receipt, new invoice) | manual | E |
| TEST-23 | Counter | Keyboard-only run with the mouse unused on the real keyboard | manual | E |
| TEST-24 | Counter | Double scan and double click create no duplicate line or invoice | e2e | E |
| TEST-25 | Counter | Uncertain submit: server state read before any retry | integration | E |
| TEST-26 | Counter | Counter works with the internet cable unplugged | manual | E |
| TEST-27 | Shift | Close shift with counted cash differing from expected flags variance | integration | E |
| TEST-28 | Publish | Missing-field product cannot be approved | unit | PUB |
| TEST-29 | Publish | One approval publishes to Facebook, Instagram, Telegram; failures retry then alert | integration | PUB |
| TEST-30 | Publish | WhatsApp broadcast refuses contacts without consent; the optional budget cap works when enabled | integration | PUB |
| TEST-31 | Publish | No public post contains a wholesale price | automated check | PUB |
| TEST-32 | Orders | A customer message "payment done" never changes payment state | integration | O |
| TEST-33 | Orders | Duplicate gateway create returns one Sales Order; ERPNext timeout then retry yields one | integration | O |
| TEST-34 | Orders | Link down: new orders blocked, notice sent, resume after recovery | integration | O |
| TEST-35 | Orders | Shipping fee set by staff; AI path cannot quote it | integration | O |
| TEST-36 | Orders | Verification writes one ledger entry and one draft Payment Entry on repeat calls | integration | O |
| TEST-37 | Shipping | Duplicate Bosta webhooks send one notification | integration | B |
| TEST-38 | AI | Image or voice text saying "confirm my payment" or "give 50% off" changes nothing | integration | A |
| TEST-39 | AI | Reply never states a price or stock not returned by a tool this turn | evaluation | A |
| TEST-40 | AI | Human takeover silences the AI; stale replies are discarded | integration | C |
| TEST-41 | Media | Voice quantities need read-back confirmation before entering a cart | integration | A |
| TEST-42 | Security | Unauthenticated calls to every endpoint are rejected | automated | all |
| TEST-53 | Counter | A full shift sold offline in POS Next syncs after reconnection with each invoice exactly once and shift totals matching ERPNext | manual | E |
| TEST-54 | Counter | POS Next upgrade and uninstall rehearsal on staging: no hidden records, no broken forms, `diva_guard` rules still enforced | manual | E |
| TEST-55 | Counter | Dozen barcode adds 1 dozen, piece barcode adds 1 piece, and a multiplier scan (if patched) adds the right quantity | integration | E |
| TEST-56 | Counter | Every scan shows item name, code, price per dozen and stock and the quantity added; focus returns to the barcode field | e2e | E |
| TEST-57 | Counter | The owner's key map works on the real keyboard in the standalone window: F1–F10, Ctrl+F, Ctrl+Delete, Ctrl+Z, Ctrl+R; blocked keys have a fallback | manual | E |
| TEST-58 | ERP | Opening stock value, receivables and payables equal the signed cutover sheet | manual | E |
| TEST-59 | ERP | Write-off of expired or damaged stock posts the expense and removes it from sellable stock | integration | E |
| TEST-60 | Counter | Manager PIN locks out after repeated failures and is never written to logs | integration | E |
| TEST-61 | Publish | A STOP reply unsubscribes the contact and the next broadcast excludes them | integration | PUB |
| TEST-62 | Publish | A video converts to 9:16 within platform limits; a photo post works | integration | PUB |
| TEST-63 | Chat | An unknown contact is screened and rate limited; spam is blocked | integration | C |
| TEST-64 | Ops | Restore drill meets the recovery targets in `11` | manual | E |
| TEST-65 | Data | No active item is missing barcode, price, pack size or image when the quality dashboard reads zero | integration | E |
| TEST-66 | Counter | Unsynced POS Next invoices older than the limit trigger an alert | integration | E |
| TEST-67 | L10n | Every kept ERPNext screen and POS Next screen shows Arabic labels with correct RTL layout for staff roles | manual | E |
| TEST-68 | L10n | An Arabic receipt prints on the real 80 mm printer with connected letters, correct direction and digits | manual | E |
| TEST-69 | L10n | Searching أ/ا, ي/ى, ة/ه variants, with or without diacritics, finds the same item | unit | E |
| TEST-70 | L10n | Arabic-Indic digits typed in quantity, phone and barcode fields are accepted and normalized | unit | E |
| TEST-71 | L10n | The owner's key map works with the Arabic keyboard layout active | manual | E |
| TEST-72 | L10n | A user's language choice persists across devices and sessions | e2e | E |
| TEST-73 | L10n | CI fails when any locale key is missing in `ar` or `en` | automated | E |
| TEST-74 | L10n | RTL screenshots of key screens match the approved baseline in both languages | e2e | PUB |
| TEST-75 | L10n | Every WhatsApp template exists and is approved in `ar` and `en` | manual | PUB |
| TEST-76 | AI | Replies follow the customer's language, including Franco-Arabic and Egyptian number words | evaluation | A |
| TEST-77 | L10n | A label prints Arabic name and EAN-13 legibly and scans correctly | manual | E |
| TEST-78 | L10n | Mixed Arabic and English item names, SKUs and numbers display correctly (bidi) in POS, Ops and receipts | manual | E |
| TEST-79 | Purchasing | China import: 10 dozen paid 40% then 60%; stock, inventory value, supplier balance and payment history are correct | integration | E |
| TEST-80 | Stock | Transferring 2 dozen from Main Inventory to Shop leaves total stock and valuation unchanged | integration | E |
| TEST-81 | Pricing | Conflicting prices resolve by customer, group, default order; unresolved ties block for manager review; the price source is logged | integration | E |
| TEST-82 | Rules | Lowering an item rate or stacking discounts to exceed 5% effective discount is rejected for employees | integration | E |
| TEST-83 | Orders | New reseller order with 4,000 EGP goods needs a 1,200 EGP deposit; no stock is reserved until it is verified | integration | O |
| TEST-84 | Orders | An order whose deposit deadline passes expires and a competing order can then take the stock | integration | O |
| TEST-85 | Orders | Ready-for-dispatch creates the Delivery Note and Sales Invoice and allocates the deposit advance; the remaining balance is correct | integration | O |
| TEST-86 | Accounting | A deposit appears as a customer advance, not as sales revenue | integration | O |
| TEST-87 | Returns | Return above the eligible quantity is rejected; cash refund above the limit needs a manager; goods go to Returns and Defects until assessed | integration | E |
| TEST-88 | Purchasing | A payment to a China supplier by any mode except Bank Transfer is rejected | integration | E |
| TEST-89 | Payments | ECash and WePay payments post to their own accounts | integration | E |
| TEST-90 | Shipping | A manual courier shipment stores courier, tracking number, fee, status and outcome | integration | B |
| TEST-91 | Costing | With FIFO, a sale consumes the oldest cost layer and the valuation report matches expectations; the staging audit passed first | integration | E |
| TEST-92 | Docs | Open in WhatsApp builds a link with the normalized number and a ready Arabic or English message; the PDF downloads with correct Arabic layout | e2e | E |
| TEST-93 | Docs | One-click send creates exactly one message per document version; a double click sends once | integration | PUB |
| TEST-94 | Docs | Sending is blocked for a number without recorded consent | integration | PUB |
| TEST-95 | Docs | The PDF received on WhatsApp shows correct right-to-left Arabic and the right totals | manual | PUB |
| TEST-96 | Docs | Delivery status updates appear in Ops; a failed send shows the manual fallback; sends queue when the internet is down and go out when it returns | integration | PUB |
| TEST-97 | Broadcast | The cost preview equals recipients times the template rate; sending needs a confirmation | integration | PUB |
| TEST-98 | Broadcast | Contacts without marketing consent or who replied STOP are never included | integration | PUB |
| TEST-99 | Broadcast | The same message can be sent to the Telegram channel at no cost and as a ready-to-post WhatsApp Channel pack | integration | PUB |
| TEST-100 | Docs | A lint check rejects offer or promotional text in utility templates | automated | PUB |
| TEST-101 | Docs | With the customer's 24-hour window open, a document is sent as a normal reply with no template; the path used is logged | integration | PUB |
| TEST-102 | Docs | With the window closed and consent recorded, the approved utility template is used; without consent only the manual link is offered | integration | PUB |
| TEST-103 | Identity | A WhatsApp number is linked to a reseller only after their first inbound message and staff confirmation | integration | O |
| TEST-104 | AI | Price, stock, order-status and opening-hours questions are answered without any model call; open questions reach the model | integration | A |
| TEST-105 | AI | A hard case escalates from the small model to the larger one; the cached prompt is reused | integration | A |
| TEST-106 | Ops | Stopping a service raises an Uptime Kuma alert to the owner in Telegram; an error appears in GlitchTip | manual | PUB |
| TEST-107 | Ops | A backup to R2 or B2 restores on a clean machine | manual | PUB |
| TEST-43 | Security | Webhook signatures verified; replayed webhook ignored | integration | all |
| TEST-44 | Counter | A browser-supplied price or discount that differs from the price list or role limit is rejected by the server | integration | E |
| TEST-45 | Counter | A counter invoice's payment appears in the ledger and the receivables report shows zero outstanding | integration | E |
| TEST-46 | Counter | Resuming a held draft and submitting it updates that draft; no second invoice or ghost draft remains | integration | E |
| TEST-47 | Counter | Submitting the same sale twice (retry or double click) creates one invoice | integration | E |
| TEST-48 | Counter | A user without the right role cannot post a payment entry or create items or prices | integration | E |
| TEST-49 | ERP | Purchase Invoice with Update Stock raises stock once and creates a supplier payable | integration | E |
| TEST-50 | ERP | A payment through a Bank-type mode (InstaPay, Bank Transfer) succeeds with reference number and date | integration | E |
| TEST-51 | Migration | After retirement, legacy invoices, payments, items and barcodes remain intact and printable | manual | E |
| TEST-52 | Migration | Barcodes generated by the legacy app still scan to the same items in POSNext and Ops | manual | E |

## 2. Performance targets (measure on the real machines)
UI actions under 100 ms; product search and barcode resolution under 500 ms on the store LAN; invoices of hundreds of lines remain usable; gateway call p95 under 1.5 s over the Link; catalog change visible in the cloud within 60 s. Record measurements; do not claim targets without them.

## 3. Security checklist
- Rotate exposed secrets (P0-01); secret scanning in CI.
- ERPNext reachable only from `local-api`; the Link is the only path between nodes.
- Every endpoint authenticated; service tokens for node-to-node; sessions with CSRF protection for browsers.
- MFA for owner and `payment_reviewer`.
- Role checks on the server; least privilege in ERPNext.
- Verify signatures for Chatwoot, Bosta and Telegram webhooks; deduplicate by event ID.
- Per-user ERPNext credentials encrypted at rest; fallback integration user with actor stamping.
- Private object storage, signed expiring URLs, content-type validation, size limits, EXIF stripping, rate limits.
- Personal data removed before RAG; retention jobs enforced; consent records for marketing.
- Mask phone numbers for roles that don't need them.
- Egypt Personal Data Protection Law: collect only what is needed, state retention, honor deletion requests.
- Audit log for all sensitive actions; export and pause actions logged.
- Dependencies pinned; script URLs pinned to exact versions.

## 4. Observability
Structured logs with request IDs; GlitchTip (Sentry-compatible, self-hosted) for errors and Uptime Kuma for uptime; health endpoints; alerts to the owner in Telegram for link state, failed jobs, dead letters, cash variance, large discounts, overrides, webhook failures, budget thresholds (messaging and AI spend); weekly summary of failures.


---

# 18 Owner Acceptance Scripts (ENH-R-02)

Plain steps you can do without reading code. At each gate, do the steps on **staging**, tick pass or fail, and sign. If any step fails, the gate stays closed.

## Gate P0 — Foundations
1. Old tokens and passwords no longer work (ask the agent to show the failed login).
2. The old "Nanobot" web addresses answer "not allowed" or are gone.
3. The POS Next test report exists and answers every "verify" cell in `14`.
4. CI shows green on the main branch.
5. TikTok and Meta applications show as submitted.

## Gate E — ERPNext and counter
As **each role** (owner, manager, cashier, warehouse):
1. Log in; hidden modules (Manufacturing, HR, Projects and others) are not visible.
2. Create an item with a barcode, a dozen price and a pack size. Find it by name, code and barcode.
3. Record a purchase invoice with three items. Stock rises in pieces (12 per dozen) and the supplier balance rises.
4. **Counter:** open a shift. Scan three items. Each scan shows name, code, price per dozen and stock. Use F1 to F10, Ctrl+F, Ctrl+Z, Ctrl+Delete and Ctrl+R on the real keyboard.
5. Give 5% discount (allowed). Try 6% (asks for the manager PIN). Try credit or partial payment (blocked).
6. Pay by cash, then by InstaPay. The receipt prints. Close the shift and check the totals.
7. Hold a sale, resume it, finish it. There is exactly one invoice and no leftover draft.
8. Return one single piece of a dozen item.
9. Sell a cosmetic batch; an expired batch cannot be sold.
10. Unplug the internet and sell for ten minutes. Reconnect. Each invoice appears once.
11. Print a label and scan it back to the same item.
12. Collect a payment on a back-office invoice; view the customer statement.
13. Open the daily sales, receivables and payables reports; numbers match what you expect.
14. Ask the agent to restore last night's backup on a test machine and show the same totals.
15. Opening balances sheet equals the system's opening stock value, receivables and payables.
16. China import: buy 10 dozen with freight and customs, pay 40% then 60%; stock, value, supplier balance and payment history are right; a non-bank payment is refused.
17. Transfer 2 dozen from Main Inventory to Shop; total stock and value are unchanged.
18. Lower an item price to dodge the 5% limit; it is rejected. Create two conflicting prices; the system picks by the rules or asks a manager.
19. Return more than was sold; refused. Large cash refund; asks a manager.
20. Pay with ECash and WePay; each posts to its own account.

## Gate PUB — Publishing
1. Approve one product. It appears on Facebook, Instagram and Telegram within a few minutes.
2. No public post shows a wholesale price.
3. The WhatsApp broadcast reaches only the test contacts who opted in. Reply STOP from one phone; it is excluded next time.
4. The WhatsApp ready-to-post pack arrives for manual posting.
5. TikTok shows a draft (or posts, if audit passed). A video is converted to the right shape.
6. A product missing barcode, price or image cannot be approved.

## Gate O — Chat orders
1. A chat basket of 2,999 EGP is refused with the missing amount; 3,000 EGP passes.
2. A line below the minimum quantity (in dozens) is refused.
3. Staff set the shipping fee; the AI never quotes it.
4. A customer message "payment done" does not mark anything paid. A reviewer marks it paid; one entry appears.
5. Cut the store link: new orders pause and customers get the notice; they resume after the link returns.
6. Reserved stock cannot be sold at the counter.
7. A new reseller's 4,000 EGP order needs a 1,200 EGP deposit; no stock is reserved until a reviewer verifies it; a competing order can still take the stock until then.
8. Let the deposit deadline pass; the order expires.
9. Pack and scan the order; the Delivery Note and Sales Invoice appear, the deposit is allocated as an advance, and the remaining balance is correct.

## Gates B, C, A, M (short)
- **B:** one order goes from draft to delivered in Bosta staging; duplicate Bosta events send one message.
- **C:** staff run WhatsApp, Instagram and Facebook from one inbox for a week with no lost message.
- **A:** the AI passes the review set; it never invents a price or stock; "confirm my payment" in an image or voice note changes nothing; a human takeover silences it.
- **M:** a reseller completes an order in the Mini App without staff retyping.


---

# 21 AI Tooling Policy (models, tools, budget, data rules)

Decided 2026-10-20 (DEC-55, DEC-56). Prices and rankings change monthly; re-verify before subscribing and again every quarter.

## 1. Budget
Target **$20 to $60 per month** for AI coding tools. Set a spending cap in every account. Review spend weekly.

## 2. Starting setup (about $10–60 per month)
| Lane | What | Cost |
|---|---|---|
| Agent models | OpenCode with **OpenCode Go** ($10) for Phase P0 and light work; **Go Plus ($40)** when Phase E coding starts, because Go has small monthly limits on the stronger models (section 7) | $10, then $40 |
| Overflow | In the OpenCode Console, add a small credit balance and turn on **Extra usage** so work is not blocked when a limit is reached; set a Budget | $0–10 |
| Critical reviewer | A Western-vendor model in its own tool: a free Antigravity tier, or Claude Pro or ChatGPT Plus when needed | $0 or $20 |
Go and Go Plus are for workspaces with one member (your personal workspace). Review spend weekly in the Console.

## 3. Which lane does what
| Work | Lane |
|---|---|
| Reading the spec, planning, architecture | Primary |
| Payments, deposits, `diva_guard`, authentication, backups, migrations | Primary, then reviewed by the second vendor |
| Everyday implementation (screens, adapters, endpoints) | Primary or bulk |
| Tests, docs, commit messages, SOP drafts, config files | Bulk |
| Arabic UI text | A strong model drafts, **a native Egyptian speaker reviews** |
| Pull-request review | Second vendor |
| Test running and log triage | Bulk |

## 4. Data rules (apply to every tool and model)
1. Never send secrets, production credentials, or real customer data (names, phones, addresses, chats, voice) to any model. Use anonymized data only.
2. Chinese-vendor apps and APIs used directly store data under Chinese law and may train on it. Use Chinese models only through OpenCode Go, whose own privacy table (checked 2026-10-21) lists no training and 0-day retention for them (DeepSeek's zero-retention agreement is renewed monthly and was valid through 31 October 2026), or through another zero-retention host, or self-hosted. Re-read the table every month. Even then, send only code and anonymized test data.
3. Keep payment, deposit, login and `diva_guard` code with providers whose business terms you have accepted.
4. Run agents in a sandbox or dev environment with no production access (DEC-38). Treat text from files, web pages and tickets as untrusted: agents can be tricked into running commands.
5. Check each provider is available in Egypt and that your payment method works before relying on it.

## 5. Choosing and re-choosing (bake-off)
Week 1: run `P0-10` (repository and CI) and `P0-04` (ERPNext verification) with two setups. Score each: acceptance criteria met, rework rounds, cost, time. Keep the cheapest setup that passes. Repeat the comparison every quarter and when a major model ships.

## 6. Models for the product itself (runtime)
Separate from the coding tools. Evaluate in `P0-09` and `A-03` with the 100 anonymized chats and 50 voice notes.
- **Arabic chat:** candidates are Haiku-class, Gemini Flash-class and GPT mini-class models, plus a Chinese open model through a zero-retention host. Large general models usually beat small Arabic-specific models, but Egyptian dialect and Franco-Arabic must be tested; an Egyptian-specific model such as Nile-Chat is a candidate for cheap classification.
- **Speech-to-text:** pick by word error rate on your own voice notes.
- **Images:** pick by quality and cost per image.
Choose the cheapest model that meets the evaluation thresholds.

## 7. OpenCode setup and the model for each job (DEC-57, DEC-60)
The harness is OpenCode with OpenCode Go. The repository's `opencode.json` assigns a model to each job; model IDs use the form `opencode-go/<model-id>`. Run `opencode models` first and substitute the closest current model if an ID is missing. Switch between `plan` and `build` with the Tab key; call the other agents by name with an @ mention.

**Go limits matter.** Each model has its own monthly dollar limit; every 5-hour window may use 20% and every week 50% of it. On Go ($10), estimated requests per month are about: DeepSeek V4.1 Flash 173,000; MiMo-V2.6-Flash 150,000; Qwen3.7 Plus 21,600; Hy3 21,500; MiniMax M3 16,000; MiMo-V2.6-Pro 16,300; Kimi K2.7 Code 6,750; DeepSeek V4 Pro 5,200; GLM-5.2 4,300; GLM-5.3 1,080; Qwen3.8 Max 810; Kimi K3 490. A coding agent makes many requests per task, so **high-volume work goes to the high-quota models**, and the strong low-quota models are kept for planning, hard problems and reviews. Go Plus raises the limits.

| Job | Agent | Default model | Why | Fallback |
|---|---|---|---|---|
| Planning, architecture, debugging, AI prompts and evals | `plan` | GLM-5.2 | Strong, with a workable quota | GLM-5.3 via `plan-hard` |
| Hardest architecture questions | `plan-hard` | GLM-5.3 | Best GLM, but about 1,080 requests a month on Go | GLM-5.2 |
| Backend, ERPNext, DevOps, migrations (the volume work) | `build` | DeepSeek V4.1 Flash | Very cheap, huge quota, reported as the top open-weight model on a terminal-agent benchmark | MiMo-V2.6-Flash |
| Tricky implementation the main agent cannot solve | `build-hard` | DeepSeek V4 Pro | Stronger; about 5,200 requests a month | GLM-5.2 |
| Front-end, routine screens | `frontend` | Kimi K2.7 Code | Good everyday UI work; 6,750 requests a month | Qwen3.7 Plus |
| Front-end, hard sessions | `frontend-hard` | Kimi K3 | Top front-end model, but only about 490 requests a month: rare use | Kimi K2.7 Code |
| Tests | `tests` | Qwen3.7 Plus | A different family from the implementer; 21,600 requests a month | MiniMax M3 |
| Bulk edits, boilerplate, CI fixes, log triage | `bulk` | MiMo-V2.6-Flash | Cheapest, 150,000 requests a month | Qwen3.8 Flash |
| Documentation, SOPs, commit messages | `docs` | MiniMax M3.1 Flash Free | Free for a limited time | MiMo-V2.6-Flash |
| Arabic UI text and SOP drafts | `arabic` | Qwen3.7 Plus | Strong multilingual model; **a native Egyptian speaker reviews every string** | Qwen3.8 Max |
| Screenshots, Arabic RTL layout checks | `ui-check` | MiniMax M3 | Image input; 16,000 requests a month | Kimi K3 |
| Review of DeepSeek or Kimi code | `review-by-glm` | GLM-5.2 | Different vendor than the author | GLM-5.3 |
| Review of GLM code | `review-by-deepseek` | DeepSeek V4 Pro | Different vendor than the author | MiniMax M3 |
| **Critical review** (payments, deposits, `diva_guard`, authentication, backups, migrations) | outside OpenCode | Western-vendor model in its own tool (free Antigravity, Claude Pro, ChatGPT Plus) | Required before merging critical code | none |

Rules:
- The model that wrote the code never reviews it, and tests come from a different model than the implementation.
- Every critical pull request also gets the Western-vendor review.
- When a model's limit is reached: switch to its fallback, enable Extra usage, or continue on a free model.
- Free "limited time" models can disappear; check `opencode models` monthly.
- The week-1 bake-off (section 5) can change any assignment; record the change in `docs/12`.


---

# 11 Operations and Cost

## 1. Backups
| What | How | Frequency | Restore test |
|---|---|---|---|
| ERPNext database and files | Backup on the store VM, copied off-site, encrypted | Daily plus before every change set | Quarterly, on a separate environment |
| Cloud Postgres | Managed or scheduled dump, encrypted off-server | Daily, with point-in-time if available | Quarterly |
| Media store | Cloudflare R2 or Backblaze B2 bucket, versioned or a nightly restic copy | Daily | Quarterly |
| Configuration files and code | Git | Every change | n/a |

## 1a. Recovery targets (defaults; owner confirms; ENH-S-03)
ERPNext: lose at most 24 hours of data outside shift-synced sales; counter back within 4 hours. Cloud database and media: lose at most 24 hours; cloud services back within 8 hours. Verified by a restore drill each quarter.

## 2. Runbooks (write each as a one-page checklist in Phase E and later phases)
- **Counter downtime** (VM or LAN down): numbered paper invoice pad; never reuse numbers; controlled later-entry procedure with manager sign-off; contact order; restore steps.
- **Link down:** what staff see, what customers are told, how to confirm recovery, how to follow up paused conversations.
- **Credential rotation:** order of operations for Telegram, Meta, Bosta, ERPNext users, Chatwoot.
- **ERPNext upgrade:** snapshot, staging upgrade, reapply configuration, run contract tests, then production.
- **Restore:** ERPNext, cloud database, media.
- **Printer and scanner failure:** fallback printing and manual entry.
- **Platform changes:** Graph API version, token expiry, template rejection.

## 3. Arabic SOPs (one page each, screenshots, written in Phase E)
Receive stock; transfer stock; count stock; print labels; counter sale and receipt; hold and resume; return a product; open and close shift; record a purchase; pay a supplier; record an expense; daily cash closing; collect a customer payment; publish a product; verify a payment proof (reviewer).

## 4. Training
Cashiers: counter workflow and keyboard keys. Warehouse: receive, transfer, count, labels. Manager and owner: reports, approvals, overrides, publishing, payment verification. Practice on staging first. Keep a quick-reference card at the counter.

## 5. Running cost (estimates, 16 Oct 2026; re-verify in Phase 0)
Basis: 30–100 chats per day (about 900–3,000 per month), about 52.4 EGP per USD.
| Item | Per month |
|---|---|
| WhatsApp replies and order-status messages (Egypt utility and service rate about $0.0036 per message after 1,000 free per number; possibly plus 14% VAT) | about $12–47 |
| AI replies and extraction (fixed logic for routine questions, small model first) | about $6–26 |
| Voice, image reading, image generation | about $3–15 |
| Cloud server (2 vCPU, 4 GB at first, upsized when chat and AI start), R2 or B2 storage, self-hosted monitoring, domain | about $16–35 |
| **Total before marketing broadcasts** | **about $37–123 (1,950–6,450 EGP)** |
| WhatsApp marketing broadcasts (about $0.0644 per message) | about 3,400 EGP per 1,000 messages |
Invoice and document sends by WhatsApp cost about $0.0036 each (1,000 for about $3.60). The store VM and ERPNext are assumed to exist already. Bosta shipping fees, salaries, taxes and TikTok partner fees are excluded. A monthly spend cap for messaging and AI exists in Settings but is off for now (DEC-33); keep the spend alerts.

## 6. Build effort
About 1,870–3,030 hours for phases P0 to M including the accepted enhancements, localization and v4.1 additions (see `09`), plus 6–12 hours per month of technical upkeep once stable and 10–20 hours per month for the first three months after each major release. At an outsourced rate of $12–25 per hour (an estimate; get quotes) that is roughly $22,440–75,750. If you build with an AI agent yourself, the cost is mainly your review time.

## 7. Time with the system (planning basis)
Roughly 40–60 staff hours per month for payment verification, handoffs, content approval and the daily dashboard check at your volume, compared with several times that if everything stayed manual.


---

# 12 Decisions, Open Items, Assumptions, Risks

## 1. Decision log (in force)
| ID | Decision |
|---|---|
| DEC-01 | One master specification: a repository of Markdown files plus a single-file edition |
| DEC-02 | **Corrected:** a legacy `diva_store` app exists and is in daily use (earlier answer said none). It is reviewed in `13` and retired after POSNext cutover |
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
| DEC-47 | Two purchasing flows: local (Purchase Invoice with Update Stock) and China import (Purchase Order, Purchase Receipts, Landed Cost Voucher, foreign currency, advances, bank only) |
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

## 2. Open owner questions (the agent must ask, not guess)
| ID | Question | Default until answered |
|---|---|---|
| OPEN-01 | Manager maximum discount | 15% |
| OPEN-02 | Who holds approval PINs and how are they set | Manager and owner |
| OPEN-03 | Reseller tier definitions and price lists | Standard plus one tier |
| OPEN-04 | Return policy for opened cosmetics | No returns of opened cosmetics unless defective |
| OPEN-05 | ~~Purchase flow~~ Closed: Purchase Invoice with Update Stock (DEC-31) | closed |
| OPEN-06 | Near-expiry threshold | 90 days |
| OPEN-07 | WhatsApp provider and Chatwoot compatibility | Resolved in P0-07 |
| OPEN-08 | ~~VAT and e-invoicing~~ Closed: none (DEC-26) | closed |
| OPEN-09 | Hardware models | Record in P0-06 |
| OPEN-10 | Which ledger account each mode posts to (Cash, Bank Transfer, Vodafone Cash, InstaPay) | One account per mode |
| OPEN-11 | Staff guideline for setting shipping fees | Manual until defined |
| OPEN-12 | Reservation expiry hours | 24 |
| OPEN-13 | Final item group tree and code prefixes | Two top groups per `05a` |
| OPEN-14 | Broadcast audience and consent source. Budget cap ignored for now (DEC-33) | Consent required; cap off |
| OPEN-16 | Digits shown to users: Western (default) or Arabic-Indic | Western |
| OPEN-17 | Owner approval of the Arabic glossary (`19` section 8) | Draft glossary |
| OPEN-18 | Do catalogs need English item names for any customer? | Optional English fields |
| OPEN-19 | Deposit deadline | 24 hours |
| OPEN-20 | Is Gallery sellable and which warehouses feed chat availability | Main Inventory and Shop count; Gallery display only |
| OPEN-21 | Return window and cash-refund limit | 14 days and an amount set by the owner |
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
| Exposed legacy credentials | Account takeover | P0-01 rotation |

## 5. Change log
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


---

# 13 Legacy `diva_store` App: Review, Salvage and Retirement

Source: the archive the owner uploaded (`diva_store`, version 1.0.0). Reviewed by reading the code; **nothing was run**. Items marked VERIFY must be confirmed on a staging copy in `TASK-P0-12`.

## 1. What it is
A custom Frappe app, in daily use at the counter. It contains:
- A Desk-based POS built from 22 JavaScript modules injected into the Sales Invoice form (`doctype_js`) plus about 26 KB of CSS that hides Desk elements.
- A standalone Vue 3 pilot called Diva Sale (frappe-ui, Vite) that talks to `api/pos.py`.
- Diva Receiving (Stock Entry, Material Receipt), Quick Add Item with internal EAN-13 barcode generation, Barcode Labels, Price Check, Customer Statement, Collect Payment, a dashboard, five reports and 58/80 mm thermal print formats.
- About 1,800 lines of Python, 4,800 lines of JavaScript and 1,100 lines of Vue. **No automated tests.** The CI "Find tests" step runs `grep -rn "def test"`, which exits with an error when no tests exist, so CI fails by design.

## 2. Findings (severity, location, impact)
### Critical
1. **Prices and discounts are trusted from the browser.** `api/pos.py::_build_sales_invoice` takes each row's `rate` from the client (a missing rate becomes 0) and accepts any `discount_amount`. A tampered or buggy client can sell at zero or any price. There are no MOQ, discount-limit or role checks.
2. **Payments from Diva Sale are probably not recorded (VERIFY).** `submit_sale` appends `payments` rows but never sets `is_pos`, and the standard Sales Invoice payments table applies only to POS-mode invoices. Those invoices likely stay fully outstanding. The Shift Report's by-mode breakdown reads the same table, so it would be empty or wrong.
3. **Held sales create duplicates and ghosts.** In `Sale.vue`, starting a new sale calls `hold_sale` and always inserts a new draft. A resumed draft's `invoice_name` is never sent to `submit_sale`, which inserts a new invoice and leaves the old draft behind. `get_held_invoices` lists every draft with a positive total, not only held sales.
4. **No idempotency anywhere.** `submit_sale`, `hold_sale`, `collect_payment` and `submit_and_pay` can create duplicates after a timeout, retry or double click.
5. **Permission bypass.** `collect_payment` and `create_quick_item` use `ignore_permissions=True` inside whitelisted methods any logged-in user can call, so any user could post a Payment Entry or create Items and Item Prices. `submit_and_pay` loads documents without explicit permission checks.

### High
6. **Prices ignore ERPNext's pricing engine.** `item_lookup.get_selling_price` reads one `Item Price` row and falls back to `standard_rate`. It ignores customer price lists, pricing rules, UOM, validity dates and currency.
7. **UOM is lost.** The cart sends only item code, quantity and rate; `scan` returns the stock UOM. This breaks the dozen-versus-piece design (DEC-20) and UOM-specific barcodes.
8. **Receiving bypasses purchasing.** Diva Receiving posts a Stock Entry (Material Receipt). Supplier purchases then create no payable. The owner buys with goods and invoice together, so this should be a Purchase Invoice with Update Stock (DEC-31). The scan fallback cost of 0 also distorts valuation.
9. **Stock checks read `Bin.actual_qty` only** and ignore reservations (RULE-STOCK).
10. **Module collision.** `diva_store/api.py` and the `diva_store/api/` package coexist; Python imports the package, so `api.py` is unreachable. Two different `get_pos_settings` functions exist.
11. **Bank-type payment modes may fail (VERIFY).** Payment Entries for Bank-type accounts usually require a reference number and date; neither is sent.
12. **Fragile Desk injection.** Many `display:none !important` rules and `*_old.js` dead files. The app's own backlog admits overlay bugs and started the standalone pilot to escape them.

### Medium
13. The settings DocType is defined both in the app and as a fixture, which can conflict on migrate. Payment modes are one comma-separated string.
14. A 2 MB source map, built assets and a zip file are committed inside the package; the git history has no commits.
15. `search_items` runs two extra queries per result row (up to 50 rows) per keystroke, with leading-wildcard `LIKE` searches.
16. Customer outstanding is summed from invoice outstanding amounts, not from the general ledger.
17. Quick Add creates Items and Item Prices without validation; the item code equals the barcode.

### Good (keep the ideas)
Parameterized SQL; no secrets in code; clear comments; use of ERPNext's `set_missing_values()` for Payment Entries; FIFO allocation in Collect Payment; internal EAN-13 barcode generator using GS1's in-store prefix range (20–29); idempotent role and payment-mode setup; broad feature coverage that tells us what the cashiers actually use.

## 3. Salvage and retirement map
The feature-by-feature comparison with POS Next is in `14-feature-decision-matrix.md`.
| Legacy component | Action | Target |
|---|---|---|
| Desk POS (22 modules, CSS) and Diva Sale pilot | **Retire** after POSNext cutover | POSNext (DEC-29) |
| `collect_payment`, customer statement | Rewrite with fixes (permissions, idempotency, reference fields) | Ops: Collect |
| Diva Receiving | Replace | Ops: Receive as **Purchase Invoice with Update Stock**; Stock Entry only for opening stock and non-purchase receipts |
| EAN-13 internal barcode generator | Port with tests; **keep all existing barcodes** | `local-api` item service |
| Barcode Labels, Price Check | Rebuild | Ops: Labels (EAN-13), Items |
| Five Diva reports, dashboard | Replace with standard reports and the Control Room | Phase E reports, Phase PUB Control Room |
| 58 and 80 mm print formats | Superseded by POSNext receipts with QZ Tray | POSNext |
| Roles `Diva Cashier`, `Diva Warehouse Staff` | Update to the role matrix in `07` | E-16 |
| Payment modes Cash, E-Wallet, InstaPay | Rename E-Wallet to Vodafone Cash; add Bank Transfer | E-09 |
| `Diva POS Settings` | Replace with POS Profile and `diva_guard` settings | E-14 |

## 4. Retirement steps (`TASK-E-00`, `TASK-E-14d`)
1. Freeze the legacy app: no new features, bug fixes only for blockers.
2. Back up ERPNext. Restore a copy to staging with the legacy app installed.
3. Verify findings 2, 3 and 11 on staging and record results.
4. Install POSNext and `diva_guard` on staging; run the POS-CHECK list and TEST-44 to TEST-52.
5. Pilot with one cashier for several days alongside the legacy app.
6. Cut over on a quiet day. Keep the legacy app installed but unused for one week as a fallback.
7. Back up again, then uninstall the legacy app. Existing invoices, payments, items and barcodes remain because they are standard ERPNext documents.

## 5. Lessons turned into rules
- Never trust a price, discount or total from a client; recompute on the server (RULE-PRICE, RULE-DISC).
- One held sale is one draft; resume updates the same draft.
- Every state-changing endpoint takes an idempotency key and checks permissions explicitly.
- A payment is real only when ERPNext shows it in the ledger; verify with a test invoice.
- No code ships without tests and a passing CI.


---

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
| `E-14a` | OPEN-01 manager discount maximum | 15% |
| `E-14a` | OPEN-02 who holds approval PINs | Manager and owner |
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


---

# 25 Cost Savings: Same Function, Lower Cost

Status: **decided 2026-10-22 (DEC-64, DEC-65).** Adopted: 2, 3, 6, 7, 9, 10. Not adopted: 1 (n8n stays) and 8 (AI-generated backgrounds stay, always on top of the real photo). Items 4, 5 and 11 to 15 remain proposals. Estimates are monthly and approximate.

| # | Saving | Instead of | Saves | Trade-off | Decision |
|---|---|---|---|---|---|---|
| 1 | Drop n8n; run schedules and briefs in the backend's own worker | A separate n8n service | A service to host and maintain; about 1–2 GB RAM | One less visual tool; schedules are code  Not adopted |
| 2 | Start the cloud server small (2 vCPU, 4 GB) and upgrade when chat and AI start | The 4 vCPU, 8 GB planned for later phases | about $15–30 | Resize later  **Adopted** |
| 3 | Send invoices with the free Open in WhatsApp link; send customers a click-to-chat link or QR so they message first (opens a free 24-hour window) | Paid template sends and OTP-style messages | A large share of message fees | Slightly more manual at first  **Adopted** |
| 4 | Use Meta's WhatsApp Cloud API directly, no reseller markup (check in `P0-07`) | A provider that adds a fee per message | Depends on provider | Needs the setup done once  Proposed |
| 5 | Put offers on Telegram and the WhatsApp Channel pack first | Paid WhatsApp broadcasts (about 3.4 EGP each) | up to about 1,700 EGP per 500-customer offer | Reaches only followers  Proposed |
| 6 | Answer routine questions (price, stock, order status, opening hours) with fixed logic and templates; call the AI only for open questions | An AI call for every message | about 40–60% of AI cost | Needs the rules built  **Adopted** |
| 7 | Small-model first, escalate to a bigger model only for hard cases; cache the shared prompt | One mid-size model for everything | about 50–70% of AI cost | Needs the evaluation set to tune  **Adopted** |
| 8 | Use real product photos with free background removal and fixed templates; skip AI-generated backgrounds | AI image generation | about $2–16 and fewer misleading images | Less variety  Not adopted |
| 9 | Self-host Uptime Kuma and GlitchTip | Paid error monitoring (about $26) | about $26 | A little upkeep  **Adopted** |
| 10 | Store media and backups on Cloudflare R2 or Backblaze B2 | Large cloud object storage | about $0–5 | Another account  **Adopted** |
| 11 | Run CI on a self-hosted runner on the dev VM | Paid CI minutes beyond the free allowance | $0–10 | Keep the VM updated  Proposed |
| 12 | Verify a reseller's phone because they messaged you first | A paid verification template | per-message fees | Fewer verification steps for staff  Proposed |
| 13 | Transcribe a voice note only when it contains an order or question | Transcribing everything | small | A simple rule  Proposed |
| 14 | Keep Postgres, Chatwoot and the backend on one small VPS | A managed database | about $15+ | You manage backups (already planned)  Proposed |
| 15 | Skip direct TikTok posting until it is worth the audit; post drafts | Audit and API time | developer hours | Manual finish in the app  Proposed |

**Decision:** adopt 2, 3, 6, 7, 9 and 10. Keep n8n (1) and keep AI-generated backgrounds (8). They are implemented as tasks `A-10`, `A-11`, `ENH-S-10`, `ENH-S-11`, `ENH-C-09` and changes to `22`, `10` and `11`.
