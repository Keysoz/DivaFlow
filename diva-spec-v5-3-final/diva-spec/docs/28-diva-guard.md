# diva_guard — server-side counter rules

`diva_guard` is the minimal custom Frappe app allowed by DEC-29. It contains
only server-side validation hooks, its own settings/approval doctypes and the
`Diva Product Rule` master. It adds no custom fields except the single owner-approved `custom_barcode`
quick-entry field (DEC-78); it changes no ERPNext core file. The rules themselves live in
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
| Manager approval | Above the cashier limit, a manager role or a single-use approval token obtained with the manager PIN is required. Approval is enforced at submit (a draft may wait); each approval is locked while consumed, stored in `Diva Override Approval` (requester, reason, amount, PIN holder, expiry) and marked used exactly once. |
| Counter credit | A non-manager cannot create an unpaid or partially paid Sales Invoice, with or without `is_pos`; this closes the "just omit is_pos" bypass. |
| Quick item entry | The Item quick entry takes a Barcode and a Selling Price (EGP/Dozen). On save the barcode is appended to the Barcodes table (duplicates rejected) and the price is written to Standard Selling when `standard_rate` changes: Dozen at the entered rate, stock UOM at rate/12 rounded (DEC-78/79). A deliberate Item Price edit is preserved on unrelated Item saves. Barcode type is left blank (set EAN manually if needed). A concurrent double-create can still race the duplicate check, as ERPNext's own barcode check is read-based too; a DB unique index would need a core schema change, which is out of scope. |
| Available stock | For stock items with a Bin, available quantity (`actual_qty − reserved_qty`) must cover the line. Negative stock remains disabled in ERPNext settings. |

Returns (`is_return`) skip the MOQ and counter-credit checks.

## Settings and PIN

`Diva Guard Settings` (Single) holds the limits and the PIN verifier:

- `enabled`, `discount_cashier_limit_pct` (5), `discount_manager_limit_pct` (15),
  `enforce_moq`, `enforce_price_list`, `block_counter_credit`,
  `enforce_reserved_stock`.
- `manager_pin_hash`, `manager_pin_salt`, `manager_pin_iterations`: PBKDF2-HMAC-
  SHA256 with at least 260,000 iterations. The PIN is **never** stored in the
  repository; `scripts/seed_diva_guard.py` reads it from `DIVA_MANAGER_PIN`
  (at least 6 characters, use the secrets manager) and stores only the hash and
  salt.

`POST /api/method/diva_guard.api.approve_discount` verifies the PIN (rate-limited
to five attempts per five minutes per user) and returns a 10-minute, single-use
token tied to the requesting user. Only a SHA-256 hash of the token is stored.
The client sends the token on the invoice submit request as:

```
X-Diva-Override-Token: <token>
```

The invoice hook consumes the token under a Redis lock, records the voucher and
marks it used; a replayed, expired or another user’s token fails. Re-validation
of the same voucher is idempotent. Approval tokens are not yet wired to the POS
Next PIN dialog; that UI patch is part of TASK-E-14b/E-14d.

## Data

- `Diva Product Rule`: one row per item — English name, publish status, MOQ and
  step in Dozen, per-item maximum discount, Arabic/English descriptions,
  keywords. Sales users can read it; the POS can cache it for offline MOQ.
- `Diva Guard Settings`: single row.
- `Diva Override Approval`: audit of PIN approvals. `user` is the requester,
  `approved_by` is the PIN holder (Administrator per OPEN-02), `approval_method`
  is `Manager PIN`; only the token hash is stored and it expires.

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

The checks cover: MOQ rejection, a compliant cashier sale created and submitted,
a cashier discount draft blocked at submit without a PIN, manager discount
allowed, PIN-token approval submitted and single-use (replay blocked), wrong-user
and expired tokens rejected, an approval below the actual discount rejected,
counter partial payment blocked, a rate above the price list blocked, a Nos line
using the Dozen price (no client-rate fallback), negative quantity and free-item
rejection, and a cashier credit invoice blocked while a manager can still create
one.

## Limits and next steps

- The POS Next PIN dialog must call `approve_discount` and send the header
  (TASK-E-14b/E-14d); until then the POS shows only the server error.
- FEFO batch selection and expired-batch blocking are provided by native ERPNext
  settings (TASK-E-14c, DEC-76); the POS Next UI still needs staging verification.
- The owner PIN is held by Administrator (OPEN-02) and rotated through the secret
  store; the seed script is the only writer.
- `diva_guard` is critical code: changes need a Western-vendor review and an
  owner-approved merge (AGENTS.md §7, DEC-56).
