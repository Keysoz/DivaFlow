# TASK P0-10 (with ENH-S-01, ENH-S-02, ENH-R-03): repository and CI

Create the monorepo skeleton described in `AGENTS.md` section 4 (`apps/`, `packages/`, `infra/`, `tests/`), with empty but runnable placeholders.
- `Makefile` with `setup`, `dev-cloud`, `dev-store`, `test`, `lint`, `e2e`, `contract`.
- Docker Compose files for the cloud node and the store node (PostgreSQL in both).
- CI: lint, type check, tests, secret scan, `pip-audit` and `npm audit`.
- Locale files `ar.json` and `en.json` and a CI check that fails when a key is missing in either.
Acceptance: `make setup test lint` pass locally and in CI. Show the CI run.
