# Cloud foundation — PUB-01

Status: **partial** (code and local tests done; VPS deployment, uptime alerts and
object storage still need the owner's cloud account).

## What exists

`apps/cloud-api` (FastAPI) now has:

- **PostgreSQL** via SQLAlchemy 2 and Alembic (`apps/cloud-api/migrations`).
- **Auth:** a single owner bootstrap guarded by a one-time `BOOTSTRAP_TOKEN`
  (constant-time compare; a partial unique index enforces one owner); passwords
  hashed with Argon2id; short-lived JWT access tokens (30 min) and refresh tokens
  stored as SHA-256 hashes (14 days). Refresh rotation is an atomic conditional
  update; replaying a rotated token revokes every session for that user.
- **MFA:** TOTP (RFC 6238) for every owner login, with secrets encrypted under a
  dedicated `MFA_ENCRYPTION_KEY` (separate from `JWT_SECRET`) and eight single-use
  recovery codes (hashed). An owner cannot obtain a token until MFA is enabled;
  staff MFA is optional and uses the same setup/enable endpoints. The secret can
  only be initialized once; a reset is an audited manual procedure.
- **Audit log:** bootstrap, MFA setup/enable/failure, login success/failure,
  refresh/reuse, logout and user creation, with actor, trusted-proxy-aware IP and
  result. `GET /admin/audit` (owner) returns the latest entries. Rows are indexed
  for the rate-limit query.
- **Health:** `GET /health` (liveness) and `GET /ready` (database check) for the
  reverse proxy and Uptime Kuma.
- **Rate limit:** five failed password/MFA attempts per email **or IP** in 15 minutes return 429; attempts are audited. The threshold is intentionally low; tune it on staging.
- Security headers and a CORS allow-list from the environment.

### Endpoints

```
POST /auth/bootstrap        X-Bootstrap-Token; one owner only; returns TOTP secret + URI
POST /auth/mfa/setup        email + password; regenerates a pending TOTP secret
POST /auth/mfa/enable       email + password + TOTP; returns recovery codes
POST /auth/login            email + password + TOTP or recovery code
POST /auth/refresh          rotate the refresh token
POST /auth/logout           revoke the refresh token
GET  /auth/me               current user
POST /admin/users           owner creates staff/admin users
GET  /admin/audit           latest audit entries (owner)
GET  /health, /ready        liveness and database readiness
```

An owner is blocked from `/auth/me` and every protected route until MFA is on
(`MFA setup required for the owner`); login returns `mfa_required` without a code.

## Run locally

```
cp infra/compose/.env.example infra/compose/.env   # fill POSTGRES_PASSWORD, JWT_SECRET, BOOTSTRAP_TOKEN
make dev-cloud
# then bootstrap once (example uses the dev defaults from .env):
curl -X POST http://localhost:8000/auth/bootstrap \
  -H 'Content-Type: application/json' \
  -H "X-Bootstrap-Token: $BOOTSTRAP_TOKEN" \
  -d '{"email":"owner@example.com","password":"a-long-password"}'
# scan the returned otpauth URI, then:
curl -X POST http://localhost:8000/auth/mfa/enable \
  -H 'Content-Type: application/json' \
  -d '{"email":"owner@example.com","password":"a-long-password","code":"123456"}'
```

Migrations run automatically in the container (`alembic upgrade head`); locally
run `uv run alembic upgrade head` from `apps/cloud-api` with `DATABASE_URL` set.

## Secrets and deployment

- `JWT_SECRET` (≥32 random bytes), `BOOTSTRAP_TOKEN` (one-time), `POSTGRES_PASSWORD`
  and `DATABASE_URL` come from the secret manager (Bitwarden, `26`), never git.
- Set `ENVIRONMENT` explicitly (`dev`, `staging`, `production`); outside `dev`,
  startup refuses the dev JWT secret, MFA key and bootstrap token. `JWT_SECRET`,
  `MFA_ENCRYPTION_KEY` and `BOOTSTRAP_TOKEN` must each be at least 32 bytes where
  applicable and come from the secret manager.
- Deploy to a small VPS first (2 vCPU/4 GB), terminate TLS at the reverse proxy,
  expose only 443, keep the API on `127.0.0.1:8000` and PostgreSQL bound to
  localhost, set `TRUSTED_PROXIES` to the proxy address, and run Uptime Kuma and
  GlitchTip (or Sentry-compatible DSN) on the same private network. HSTS is sent
  when `ENVIRONMENT=production`.
- Back up PostgreSQL daily and test a restore quarterly; store copies in R2/B2.

## Lost password / lost MFA device

There is no self-service reset (by design). The owner must:

1. Stop the API or use a maintenance shell on the VPS (never edit production data
   from an agent session).
2. Record the action in the audit log/runbook.
3. Clear the affected user's `totp_secret_encrypted`, `mfa_enabled` and
   `recovery_codes_hashed` with a reviewed SQL statement, force a password reset,
   then re-run MFA setup/enable. The owner's new secret is scanned immediately.
4. Rotate `JWT_SECRET` if a token may be compromised (this signs out everyone).

This procedure is pending an audited admin CLI; until then it is a documented
manual operation for the owner only.

## Known test gap

The suite runs against SQLite; a PostgreSQL integration test (refresh/timestamps)
still needs a reachable Postgres in CI or staging. The Docker Hub pull was not
available in this session, so it could not be run locally.

## Pending owner actions

- Create the cloud VPS/domain, DNS and TLS; provide the provider account.
- Provide the GlitchTip/Sentry DSN (or approve self-hosted GlitchTip) and the
  Uptime Kuma monitor target.
- Approve the object-storage bucket (R2 or B2) for media/backups.

## Next tasks

PUB-02 (WireGuard link, catalog sync), PUB-03 (Telegram bot skeleton), PUB-04
(Control Room shell). The database models and auth are ready for them.
