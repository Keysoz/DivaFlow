# 17 Agent Onboarding Package (ENH-R-01)

What the owner prepares before the coding agent starts. The agent works on **development and staging only**. It never receives production administrator credentials (DEC-38).

## 1. Accounts and access
| # | Item | Needed by | Notes |
|---|---|---|---|
| 1 | Private Git repository, branch protection, CI enabled | P0-10 | Agent works on branches; the owner merges |
| 2 | Secrets manager account (for example Doppler, 1Password or SOPS with age) | P0 | Never paste secrets in chat or files |
| 3 | Cloud VPS account and region (decided in P0-05) | P0-05 | Dev and staging first |
| 4 | **ERPNext:** you do not need an existing site. `P0-04a` installs a disposable dev instance and `E-00a` installs production. If an old site exists, a restored copy helps `P0-12` (optional) | P0-03, P0-04 | Customer data is real until anonymized; restrict access |
| 5 | Secure access to the store VM for staging work (WireGuard or Tailscale) | P0 | No production admin for the agent |
| 6 | Item master export (CSV): code, name, group, barcode, price, pack, image | P0-09 | Basis for the field register and data quality |
| 7 | New Telegram bot token (the old one is exposed) | P0-01 | Create after rotating |
| 8 | Meta Business Manager access for testing; Facebook Page and Instagram professional account linked | P0-07, PUB-07 | Add the developer as tester or admin |
| 9 | Current WhatsApp Business API provider access and template list | P0-07 | Needed for Chatwoot compatibility |
| 10 | TikTok developer account and app | P0-11 | Audit takes time |
| 11 | Bosta business account and staging API key | B | Needed later |
| 12 | Domain name and DNS access | PUB-01 | Webhooks and dashboards |
| 13 | Hardware reachable for tests: barcode scanner, 80 mm receipt printer, label printer, a counter PC | P0-06 | Record model numbers |
| 14 | 100 anonymized chats and 50 voice notes | P0-09 | Remove names, phones, addresses |
| 15 | Environment facts (last known): ERPNext 16.30.0, Frappe 16.29.0, site `erp.divastore.local`, bench `~/diva-erp/frappe-bench`, private Debian VM. **Verify on the real machine before relying on them** | P0-04 | |
| 16 | China supplier list with currencies, typical order and payment pattern (40% and 60%), freight and customs cost types | E-08b | |
| 17 | Current valuation setting and stock history export | E-07 | For the FIFO audit |

## 2. Business material
Logo and colors; brand voice notes and 10 sample captions you like (ENH-M-01); reseller terms (ENH-L-01); privacy and consent wording (ENH-L-02); return policy for opened cosmetics (OPEN-04); item group tree (OPEN-13); price tiers (OPEN-03); opening balances sheet (ENH-A-01); list of staff with roles and PIN holders (OPEN-02).

## 3. Working agreement
- One channel for questions (for example a shared chat) and a daily written status from the agent.
- The agent asks instead of guessing when a business rule is missing.
- The owner reviews with the acceptance scripts in `18-owner-acceptance-scripts.md` and signs each gate.
- Nothing is deployed to production without the owner's approval and a fresh backup.

## 4. Agent safety rules
No production credentials. No destructive commands (drop, delete, truncate) without a backup and explicit approval. No real customer messages sent from dev or staging. Use test accounts. Report every secret that appears anywhere so it can be rotated.
