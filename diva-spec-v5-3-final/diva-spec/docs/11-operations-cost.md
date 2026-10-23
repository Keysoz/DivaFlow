# 11 Operations and Cost

## 1. Backups
| What | How | Frequency | Restore test |
|---|---|---|---|
| ERPNext database and files | Backup on the store VM, copied off-site, encrypted | Daily plus before every change set | Quarterly, on a separate environment |
| Cloud Postgres | Managed or scheduled dump, encrypted off-server | Daily, with point-in-time if available | Quarterly |
| Media store | Cloudflare R2 or Backblaze B2 bucket, versioned or a nightly restic copy | Daily | Quarterly |
| Configuration files and code | Git | Every change | n/a |

## 1a. Recovery targets (defaults; owner confirms; ENH-S-03)
ERPNext: lose at most 24 hours of data outside shift-synced sales; counter back within 4 hours. Cloud database and media: lose at most 24 hours; cloud services back within 8 hours. Verified by a restore drill each quarter.

## 2. Runbooks (write each as a one-page checklist in Phase E and later phases)
- **Counter downtime** (VM or LAN down): numbered paper invoice pad; never reuse numbers; controlled later-entry procedure with manager sign-off; contact order; restore steps.
- **Link down:** what staff see, what customers are told, how to confirm recovery, how to follow up paused conversations.
- **Credential rotation:** order of operations for Telegram, Meta, Bosta, ERPNext users, Chatwoot.
- **ERPNext upgrade:** snapshot, staging upgrade, reapply configuration, run contract tests, then production.
- **Restore:** ERPNext, cloud database, media.
- **Printer and scanner failure:** fallback printing and manual entry.
- **Platform changes:** Graph API version, token expiry, template rejection.

## 3. Arabic SOPs (one page each, screenshots, written in Phase E)
Receive stock; transfer stock; count stock; print labels; counter sale and receipt; hold and resume; return a product; open and close shift; record a purchase; pay a supplier; record an expense; daily cash closing; collect a customer payment; publish a product; verify a payment proof (reviewer).

## 4. Training
Cashiers: counter workflow and keyboard keys. Warehouse: receive, transfer, count, labels. Manager and owner: reports, approvals, overrides, publishing, payment verification. Practice on staging first. Keep a quick-reference card at the counter.

## 5. Running cost (estimates, 16 Oct 2026; re-verify in Phase 0)
Basis: 30–100 chats per day (about 900–3,000 per month), about 52.4 EGP per USD.
| Item | Per month |
|---|---|
| WhatsApp replies and order-status messages (Egypt utility and service rate about $0.0036 per message after 1,000 free per number; possibly plus 14% VAT) | about $12–47 |
| AI replies and extraction (fixed logic for routine questions, small model first) | about $6–26 |
| Voice, image reading, image generation | about $3–15 |
| Cloud server (2 vCPU, 4 GB at first, upsized when chat and AI start), R2 or B2 storage, self-hosted monitoring, domain | about $16–35 |
| **Total before marketing broadcasts** | **about $37–123 (1,950–6,450 EGP)** |
| WhatsApp marketing broadcasts (about $0.0644 per message) | about 3,400 EGP per 1,000 messages |
Invoice and document sends by WhatsApp cost about $0.0036 each (1,000 for about $3.60). The store VM and ERPNext are assumed to exist already. Bosta shipping fees, salaries, taxes and TikTok partner fees are excluded. A monthly spend cap for messaging and AI exists in Settings but is off for now (DEC-33); keep the spend alerts.

## 6. Build effort
About 1,870–3,030 hours for phases P0 to M including the accepted enhancements, localization and v4.1 additions (see `09`), plus 6–12 hours per month of technical upkeep once stable and 10–20 hours per month for the first three months after each major release. At an outsourced rate of $12–25 per hour (an estimate; get quotes) that is roughly $22,440–75,750. If you build with an AI agent yourself, the cost is mainly your review time.

## 7. Time with the system (planning basis)
Roughly 40–60 staff hours per month for payment verification, handoffs, content approval and the daily dashboard check at your volume, compared with several times that if everything stayed manual.
