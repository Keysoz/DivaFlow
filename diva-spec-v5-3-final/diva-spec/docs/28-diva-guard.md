# diva_guard — server-side counter rules

`diva_guard` is the minimal custom Frappe app allowed by DEC-29. It contains
only server-side validation hooks, its own settings/approval doctypes and the
`Diva Product Rule` master. It adds **no custom fields** to ERPNext doctypes and
changes no ERPNext core file. The rules themselves live in
`packages/rules-engine` (pure Python); this app only maps ERPNext documents onto
them.

Scope: TASK-E-14a. Owner of the business rules: `docs/04-business-rules.md`.

## What is enforced

On every Sales Invoice `validate` (POS Next, desk and API clients alike):

| Rule | Behaviour |
|---|---|
| MOQ / step | Quantity in Dozen must meet `Diva Product Rule.moq_dozen` and step. Stock quantity is converted from Nos (1 Dozen = 12 Nos). |
| Price integrity | The authoritative rate comes from `Item Price` for the invoice price list; a rate above the list is rejected. A POS profile must use its configured selling price list. |
| Effective discount | Discount is measured on the price-list subtotal minus the net subtotal (item and invoice discounts stack). Cashier limit 5%, manager limit 15% (settings). |
| Manager approval | Above the cashier limit, a manager role or a single-use approval token obtained with the manager PIN is required. Every approval is stored in `Diva Override Approval` (actor, reason, amount, approver, expiry). |
| Counter credit | A non-manager cannot create an unpaid or partially paid Sales Invoice, with or without `is_pos`; this closes the "just omit is_pos" bypass. |
| Available stock | For stock items with a Bin, available quantity (`actual_qty − reserved_qty`) must cover the line. Negative stock remains disabled in ERPNext settings. |

Returns (`is_return`) skip the MOQ and counter-credit checks.

## Settings and PIN

`Diva Guard Settings` (Single) holds the limits and the PIN verifier:

- `enabled`, `discount_cashier_limit_pct` (5), `discount_manager_limit_pct` (15),
  `enforce_moq`, `enforce_price_list`, `block_counter_credit`,
  `enforce_reserved_stock`.
- `manager_pin_hash`, `manager_pin_salt`, `manager_pin_iterations`: PBKDF2-HMAC-
  SHA256. The PIN is **never** stored in the repository; `scripts/seed_diva_guard.py`
  reads it from `DIVA_MANAGER_PIN` (use the secrets manager) and stores only the
  hash and salt.

`POST /api/method/diva_guard.api.approve_discount` verifies the PIN (rate-limited
to five attempts per five minutes per user) and returns a 10-minute, single-use
token tied to the requesting user. The client sends it on the invoice request as:

```
X-Diva-Override-Token: <token>
```

The invoice hook consumes the token, records the voucher and marks it used. A
replayed token fails. Approval tokens are not yet wired to the POS Next PIN
dialog; that UI patch is part of TASK-E-14b/E-14d.

## Data

- `Diva Product Rule`: one row per item — English name, publish status, MOQ and
  step in Dozen, per-item maximum discount, Arabic/English descriptions,
  keywords. Sales users can read it; the POS can cache it for offline MOQ.
- `Diva Guard Settings`: single row.
- `Diva Override Approval`: audit of PIN approvals (token hash is not printed;
  the token itself is a random URL-safe string and expires).

## Install and test (dev/staging only)

```
# 1. install the app + rules-engine into the dev bench (idempotent)
./scripts/install_diva_guard.sh

# 2. seed settings and product rules (PIN from the secret store)
ERPNEXT_URL=http://localhost:8080 ERPNEXT_USER=Administrator ERPNEXT_PASSWORD=... \
  DIVA_MANAGER_PIN=... uv run python scripts/seed_diva_guard.py

# 3. run the server-rule checks with real staff accounts
ERPNEXT_URL=http://localhost:8080 ERPNEXT_USER=Administrator ERPNEXT_PASSWORD=... \
  DIVA_TEST_PASSWORD=... DIVA_MANAGER_PIN=... uv run python scripts/test_diva_guard.py
```

The checks cover: MOQ rejection, a compliant cashier sale, cashier discount above
5% blocked, manager discount allowed, PIN-token approval allowed and single-use,
counter partial payment blocked, a rate above the price list blocked, and a
cashier credit invoice blocked while a manager can still create one.

## Limits and next steps

- The POS Next PIN dialog must call `approve_discount` and send the header
  (TASK-E-14b/E-14d); until then the POS shows only the server error.
- FEFO batch selection and expired-batch blocking (TASK-E-14c) are not in this
  version; ERPNext batch/expiry is not enabled on the dev items yet.
- The owner PIN is held by Administrator (OPEN-02) and rotated through the secret
  store; the seed script is the only writer.
- `diva_guard` is critical code: changes need a Western-vendor review and an
  owner-approved merge (AGENTS.md §7, DEC-56).
