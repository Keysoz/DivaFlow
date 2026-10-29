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

## Desk layout

`desk.yaml` holds the Desk organization as data:

```yaml
dashboard_charts:      # sales trend, item mix, payments, top customers/suppliers, ageing
number_cards:          # today, month, receivables, stock value, customers, payables, guard
workspaces:            # Diva Store, Diva Reports, Diva Guard (shortcuts, links, charts, cards)
```

`apply_desk.py` creates/updates those records and is idempotent. `make
config-dry-run` and `make config-apply` run both scripts.

## Run

Credentials come from the environment (never commit them):

```bash
export ERPNEXT_URL=http://localhost:8080            # https://… on the store LAN
export ERPNEXT_USER=Administrator ERPNEXT_PASSWORD=…  # dev only
# or, preferred: ERPNEXT_API_KEY / ERPNEXT_API_SECRET

python3 infra/erpnext-config/apply.py --config infra/erpnext-config/config.yaml            # dry run
python3 infra/erpnext-config/apply.py --config infra/erpnext-config/config.yaml --apply    # write
python3 infra/erpnext-config/apply_desk.py --config infra/erpnext-config/desk.yaml         # dry run
python3 infra/erpnext-config/apply_desk.py --config infra/erpnext-config/desk.yaml --apply # write
```

The dry run prints one line per entry (`create` / `update` / `noop` / `missing`). Re-running after an apply must print **0 changes** — that is the idempotency check. Reapply after every upgrade (DEC-35 / E-03 acceptance).

## Scope

- Property setters: Check-type properties (hidden, read-only) by default; set `property_type: Data` on an entry for a non-check property such as a text default.
- Workspaces: global visibility (`is_hidden`) and, for the Diva workspaces, shortcuts, links, charts and cards (`desk.yaml`). Per-role refinement lands with the roles/users task (E-16).
