# 25 Cost Savings: Same Function, Lower Cost

Status: **decided 2026-10-22 (DEC-64, DEC-65).** Adopted: 2, 3, 6, 7, 9, 10. Not adopted: 1 (n8n stays) and 8 (AI-generated backgrounds stay, always on top of the real photo). Items 4, 5 and 11 to 15 remain proposals. Estimates are monthly and approximate.

| # | Saving | Instead of | Saves | Trade-off | Decision |
|---|---|---|---|---|---|---|
| 1 | Drop n8n; run schedules and briefs in the backend's own worker | A separate n8n service | A service to host and maintain; about 1–2 GB RAM | One less visual tool; schedules are code  Not adopted |
| 2 | Start the cloud server small (2 vCPU, 4 GB) and upgrade when chat and AI start | The 4 vCPU, 8 GB planned for later phases | about $15–30 | Resize later  **Adopted** |
| 3 | Send invoices with the free Open in WhatsApp link; send customers a click-to-chat link or QR so they message first (opens a free 24-hour window) | Paid template sends and OTP-style messages | A large share of message fees | Slightly more manual at first  **Adopted** |
| 4 | Use Meta's WhatsApp Cloud API directly, no reseller markup (check in `P0-07`) | A provider that adds a fee per message | Depends on provider | Needs the setup done once  Proposed |
| 5 | Put offers on Telegram and the WhatsApp Channel pack first | Paid WhatsApp broadcasts (about 3.4 EGP each) | up to about 1,700 EGP per 500-customer offer | Reaches only followers  Proposed |
| 6 | Answer routine questions (price, stock, order status, opening hours) with fixed logic and templates; call the AI only for open questions | An AI call for every message | about 40–60% of AI cost | Needs the rules built  **Adopted** |
| 7 | Small-model first, escalate to a bigger model only for hard cases; cache the shared prompt | One mid-size model for everything | about 50–70% of AI cost | Needs the evaluation set to tune  **Adopted** |
| 8 | Use real product photos with free background removal and fixed templates; skip AI-generated backgrounds | AI image generation | about $2–16 and fewer misleading images | Less variety  Not adopted |
| 9 | Self-host Uptime Kuma and GlitchTip | Paid error monitoring (about $26) | about $26 | A little upkeep  **Adopted** |
| 10 | Store media and backups on Cloudflare R2 or Backblaze B2 | Large cloud object storage | about $0–5 | Another account  **Adopted** |
| 11 | Run CI on a self-hosted runner on the dev VM | Paid CI minutes beyond the free allowance | $0–10 | Keep the VM updated  Proposed |
| 12 | Verify a reseller's phone because they messaged you first | A paid verification template | per-message fees | Fewer verification steps for staff  Proposed |
| 13 | Transcribe a voice note only when it contains an order or question | Transcribing everything | small | A simple rule  Proposed |
| 14 | Keep Postgres, Chatwoot and the backend on one small VPS | A managed database | about $15+ | You manage backups (already planned)  Proposed |
| 15 | Skip direct TikTok posting until it is worth the audit; post drafts | Audit and API time | developer hours | Manual finish in the app  Proposed |

**Decision:** adopt 2, 3, 6, 7, 9 and 10. Keep n8n (1) and keep AI-generated backgrounds (8). They are implemented as tasks `A-10`, `A-11`, `ENH-S-10`, `ENH-S-11`, `ENH-C-09` and changes to `22`, `10` and `11`.
