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
