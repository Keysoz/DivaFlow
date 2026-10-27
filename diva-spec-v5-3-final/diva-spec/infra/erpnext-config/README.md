# ERPNext configuration (idempotent) — TASK-E-03, TASK-E-02

Configuration is stored as data and applied only through `apply.py` (AGENTS.md §2). No core files, Server Scripts or custom fields are created.

## Config

`config.yaml` holds two sections:

```yaml
property_setters:      # hide / default / read-only, applied through Property Setter
  - doctype: Sales Invoice
    fieldname: tax_id
    property: hidden
    value: 1
workspaces:            # hide unneeded workspaces for staff (E-02)
  - name: HR
    hidden: true
```

## Run

Credentials come from the environment (never commit them):

```bash
export ERPNEXT_URL=http://localhost:8080            # https://… on the store LAN
export ERPNEXT_USER=Administrator ERPNEXT_PASSWORD=…  # dev only
# or, preferred: ERPNEXT_API_KEY / ERPNEXT_API_SECRET

python3 infra/erpnext-config/apply.py --config infra/erpnext-config/config.yaml            # dry run
python3 infra/erpnext-config/apply.py --config infra/erpnext-config/config.yaml --apply    # write
```

The dry run prints one line per entry (`create` / `update` / `noop` / `missing`). Re-running after an apply must print **0 changes** — that is the idempotency check. Reapply after every upgrade (DEC-35 / E-03 acceptance).

## Scope

- Property setters: hidden, read-only, default (any Property Setter property).
- Workspaces: global visibility (`is_hidden`). Per-role refinement lands with the roles/users task (E-16).
