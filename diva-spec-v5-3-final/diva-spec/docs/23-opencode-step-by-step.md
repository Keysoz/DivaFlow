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
