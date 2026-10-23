# Diva

Wholesale operations platform for Diva Store: simplified ERPNext, counter POS (POS Next), staff screens, publishing, chat orders, AI agent, Mini App.

- **Specification:** start at `docs/00-index.md` (v5.3 FINAL). Rules for coding agents: `AGENTS.md`.
- **Fewest-steps setup:** `docs/24-autopilot-setup.md`, then `scripts/bootstrap-dev-vm.sh`.
- **OpenCode step by step:** `docs/23-opencode-step-by-step.md`.
- **Agent setup:** `opencode.json` (a model for each job) and `docs/21-ai-tooling-policy.md`.
- **Task list:** `tasks.csv`; create GitHub issues with `scripts/create_issues.py`.
- **How to build with an agent:** `docs/20-start-here.md` and the copy-paste prompts in `prompts/`.
- **Build order:** P0, E (ERPNext), PUB (publishing), O, B, C, A, M, G (`docs/09-build-plan.md`).
