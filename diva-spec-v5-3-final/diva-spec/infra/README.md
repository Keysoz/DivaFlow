# Infra

- `compose/cloud.yml` — cloud node: `cloud-api` and PostgreSQL.
- `compose/store.yml` — store node: `local-api`.
- Dev ERPNext is not here: TASK-P0-04a starts a disposable ERPNext 16 with `scripts/start-dev-erpnext.sh`.
- Copy `compose/.env.example` to `compose/.env` (never committed) before `make dev-cloud`.
- WireGuard and backup scripts arrive with TASK-PUB-02 and TASK-E-17.
