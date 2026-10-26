# 26 Secrets Management and Rotation (ENH-S-02)

Decided 2026-10-27 (DEC-69): **Bitwarden** is the secrets manager.

- **Bitwarden Secrets Manager** holds machine secrets (API tokens, keys, database passwords) as project items; a **Bitwarden organization vault** holds human credentials (owner and staff logins). Two-factor authentication is mandatory. One collection/project per environment: `diva-prod`, `diva-staging`, `diva-dev`.
- Why Bitwarden: open source and independently audited, self-hostable if ever needed, low cost for a small team, machine accounts with scoped access tokens, built-in rotation reminders, and no per-seat lock-in.
- The agent never receives vault access (DEC-38). It works with disposable dev values only and stops if any secret appears in a repository, workflow or log.

## 1. Rules (restating AGENTS.md)

1. No secret in code, workflow, log, issue or chat. Secrets are injected as environment variables or read from Bitwarden at deploy time.
2. Production credentials are entered by the owner, never by the agent.
3. CI scans for secrets on every run (`make secret-scan`, gitleaks) and audits dependencies (`make audit`, pip-audit).
4. A secret that may have leaked is revoked first, then rotated; the incident is recorded in the risk register (`docs/12` section 4).
5. `docs/12` is updated when the rotation procedure changes.

## 2. Secret inventory and rotation schedule

| Secret | Used by | Consumed as | Owner | Rotate |
|---|---|---|---|---|
| Telegram bot token (admin bot, alerts) | cloud-api | `TELEGRAM_BOT_TOKEN` | Owner | 90 days, or on exposure |
| Meta app secret | cloud-api (webhooks) | `META_APP_SECRET` | Owner | 90 days |
| WhatsApp Cloud API token and phone-number ID | cloud-api | `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID` | Owner | 60–90 days |
| Instagram / Facebook Page tokens | publishing | `META_PAGE_TOKEN` | Owner | 60 days |
| Chatwoot webhook signing token | cloud-api | `CHATWOOT_WEBHOOK_SECRET` | Owner | 90 days |
| Bosta API key | local-api, cloud-api | `BOSTA_API_KEY` | Owner | 90 days |
| ERPNext API key and secret per staff member (DEC-09) | local-api | encrypted per user | Owner | 90 days, and on staff exit |
| AI provider keys (runtime models) | cloud-api | provider-specific env names | Owner | 90 days |
| Database passwords (cloud and store) | compose, CI | `POSTGRES_PASSWORD`, `DB_PASSWORD` | Owner | 90 days |
| Cloudflare R2 / Backblaze B2 keys (media, backups) | cloud-api, infra | `S3_*` | Owner | 90 days |
| WireGuard private keys | infra | `WG_PRIVATE_KEY` | Owner | 180 days, and on device change |
| Backup encryption key | infra | `BACKUP_ENCRYPTION_KEY` | Owner | Yearly, or on exposure |
| GitHub deploy key / token | CI | GitHub repository secret | Owner | 90 days; prefer OIDC over long-lived tokens |

Review the whole list **quarterly** (calendar reminder). Record each rotation in the Bitwarden item notes: date, who rotated, and why.

## 3. Owner setup (one-time, about 30 minutes)

1. Create the Bitwarden account and organization; enable two-factor authentication and save recovery codes offline.
2. Create the three collections (`diva-prod`, `diva-staging`, `diva-dev`) and a Secrets Manager project for each.
3. Add the items from section 2. **Start by entering the current values, then rotate the exposed ones** (P0-01) and replace them — the vault should never keep a value known to be exposed.
4. Create machine accounts for CI/deploy with least privilege (read-only on `diva-prod`, read-only or write on `diva-staging`, write on `diva-dev`); store their access tokens as GitHub repository secrets, never in files.
5. Put the owner's second device (phone) in the organization for recovery; document the break-glass procedure offline.
6. Tell the agent when the vault exists; the agent will then confirm that no file references a real value and that CI scans stay green.

## 4. Emergency rotation (suspected exposure)

1. **Revoke** the credential at the provider immediately (do not wait for the rotation date).
2. Create the replacement in Bitwarden and update the deploy environment.
3. Check provider audit logs and application logs for use of the old value; if anything looks wrong, treat it as an incident and notify the owner.
4. Record date, secret, cause and action in the risk register (`docs/12` section 4) and the Bitwarden item.
5. Run `make secret-scan` and `make audit`; both must be clean before the next deploy.

## 5. What remains manual

- Creating the Bitwarden account/organization and machine accounts (owner).
- Entering and rotating the real credentials (owner; P0-01).
- Reviewing the quarterly rotation reminder.
