# Appendix: Backup and restore rehearsal (TASK-P0-09)

**Status: partial — same-host restore proven (2026-10-27); the separate-VM proof and the datasets remain owner actions.** Everything below ran on the disposable dev stack (section 1 of `appendix-erpnext-verification.md`) with synthetic data; no production credentials were used (DEC-38).

Environment: site `frontend` on erpnext 16.52.1 / frappe 16.53.0 with pos_next 1.17.0 (pinned tag `v2.0.0`), MariaDB 11.8 inside the compose stack.

## 1. Rehearsed procedure

1. **Backup** the site with files:
   `bench --site frontend backup --with-files`
   Produced (in `sites/frontend/private/backups/`): database `1.2 MB`, public files `10 KiB`, private files `10 KiB`, plus the site-config backup.
2. **Create an empty target site:**
   `bench new-site restore-test --db-root-username root --db-root-password "$DB_ROOT_PASSWORD" --admin-password "$ADMIN_PASSWORD"`
3. **Restore** into it:
   `bench --site restore-test --force restore <db.sql.gz> --db-root-username root --db-root-password "$DB_ROOT_PASSWORD" --with-public-files <files.tar> --with-private-files <private.tar>`
   *Gotcha:* without the `--db-root-*-password` flags, `restore` prompts and, in a non-interactive shell, ends without restoring. Always pass them explicitly (from the environment; never from the repository).
4. **Verify:** the app list and the row counts matched the source exactly (table below).
5. **Clean up:** `bench drop-site restore-test --db-root-username root --db-root-password "$DB_ROOT_PASSWORD" --no-backup --force` (site archived, removed from `sites`).

## 2. Verification result

| Check | Source `frontend` | Restored `restore-test` |
|---|---|---|
| Apps | frappe 16.53.0, erpnext 16.52.1, pos_next 1.17.0 | same |
| Item | 1 | 1 |
| Customer | 2 | 2 |
| Sales Invoice | 2 | 2 |
| Sales Order | 3 | 3 |
| Custom Field | 33 | 33 |
| UOM | 240 | 240 |
| Company | 1 | 1 |
| Warehouse | 5 | 5 |
| Bin | 1 | 1 |
| Record `ACC-SINV-2026-00002` | present | present |
| Item `P004-DOZEN` | present | present |

## 3. Findings

- The backup/restore path works on ERPNext 16 with POS Next installed: the restore brings the installed-app list, custom fields, stock, invoices and the POS data.
- The database root password is required explicitly for `new-site`, `restore` and `drop-site`; keep it in the environment or the secret manager, never in a script or the repository (`26-secrets-and-rotation.md`).
- A restore is only as good as the backup cadence: the scheduled daily backup, the off-site encrypted copy and the store-VM restore belong to TASK-E-17; this rehearsal validates the manual path and the data integrity.
- **The separate-VM proof required by P0-09 is still open**: it needs the owner's second VM (or a disposable cloud VM). Running it on the same host proves the commands and the data, not the recovery from a lost machine.
- The datasets — item master export, 100 anonymized chats, 50 voice notes — are owner-provided. Real customer data must never be sent to any model (docs/21 section 4); anonymize locally first.

## 4. Gaps for later tasks

- TASK-E-17: scheduled backups, off-site encrypted copy, restore test on the store VM, downtime runbook, retention policy.
- Owner: the separate VM for the P0-09 proof, and the three datasets.
