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
