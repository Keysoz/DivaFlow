# Session start (paste at the beginning of every task; replace TASK-ID)

You are working on the Diva project. First read `AGENTS.md` and `docs/00-index.md`. Your task is **TASK-ID** from `docs/09-build-plan.md`.

1. Read the spec sections that apply to this task. In your own words, summarize the task, its acceptance criteria, dependencies and anything unclear. If a business rule is missing, ask me. Do not guess.
2. Use the `plan` agent for the plan. Propose a short plan: files to change, tests to write, risks. **Wait for my approval before editing anything.**
3. After approval, switch to `build` (use `frontend`, `tests`, `docs`, `arabic` or `bulk` for those jobs, per `docs/21`). Create a branch named `TASK-ID-short-name`. Make small commits. Write tests first where possible.
4. Run the tests and linters. Paste the exact commands and their real results.
5. Before the pull request, ask the reviewer agent that is NOT the author's model (`review-by-glm` or `review-by-deepseek`) to review it. For critical code, stop and tell me: a Western-vendor review is required (`prompts/07`).
6. Open a pull request using the template. Do not merge it.

Rules: stay inside this task. Never use production credentials. Never put secrets in files, logs or chat. Nothing may mark a payment as verified automatically. Report anything surprising or any secret you notice.
