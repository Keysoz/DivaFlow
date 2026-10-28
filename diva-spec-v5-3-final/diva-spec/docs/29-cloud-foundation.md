# Cloud foundation — PUB-01

Status: **partial** (code and local tests done; VPS deployment, uptime alerts and
object storage still need the owner's cloud account).

## What exists

`apps/cloud-api` (FastAPI) now has:

- **PostgreSQL** via SQLAlchemy 2 and Alembic (`apps/cloud-api/migrations`).
- **Auth:** owner bootstrap guarded by `BOOTSTRAP_TOKEN`; passwords hashed with
  Argon2id; short-lived JWT access tokens (30 min) and rotating refresh tokens
  stored as SHA-256 hashes (14 days).
- **MFA:** TOTP (RFC 6238) for every owner login, with encrypted secrets at rest
  and eight single-use recovery codes (hashed). An owner cannot obtain a token
  until MFA is enabled; staff MFA is optional and can be enabled with the same
  setup/enable endpoints.
- **Audit log:** bootstrap, MFA setup/enable/failure, login success/failure,
  refresh, logout and user creation, with actor, IP and result. `GET /admin/audit`
  (owner) returns the latest entries.
- **Health:** `GET /health` (liveness) and `GET /ready` (database check) for the
  reverse proxy and Uptime Kuma.
- **Login rate limit:** five failed password attempts per email in 15 minutes return 429; attempts are audited.
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
- Production must set `ENVIRONMENT=production`; startup refuses the dev JWT secret
  and bootstrap token.
- Deploy to a small VPS first (2 vCPU/4 GB), terminate TLS at the reverse proxy,
  expose only 443, keep PostgreSQL bound to localhost, and run Uptime Kuma and
  GlitchTip (or Sentry-compatible DSN) on the same private network.
- Back up PostgreSQL daily and test a restore quarterly; store copies in R2/B2.

## Pending owner actions

- Create the cloud VPS/domain, DNS and TLS; provide the provider account.
- Provide the GlitchTip/Sentry DSN (or approve self-hosted GlitchTip) and the
  Uptime Kuma monitor target.
- Approve the object-storage bucket (R2 or B2) for media/backups.

## Next tasks

PUB-02 (WireGuard link, catalog sync), PUB-03 (Telegram bot skeleton), PUB-04
(Control Room shell). The database models and auth are ready for them.
