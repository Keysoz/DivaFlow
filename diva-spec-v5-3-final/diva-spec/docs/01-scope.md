# 01 Scope

## Business
Diva Store, Egypt. Sales in EGP; China import purchases may use a foreign currency. An **on-site wholesale shop** that buys from traders and sells to traders. **All buying and selling is by the dozen (1 dozen = 12 pieces)**; there is no manufacturing. Categories: **women's accessories and jewelry** and **makeup and cosmetics**. Initial area Cairo and Giza, with nationwide shipping through Bosta for chat orders. Team: owner, manager, two employees. ERPNext 16 on a private VM at the store.

## Owner priority (DEC-03)
1. **ERPNext**: simplified, in dozens, with purchasing, counter sales and POS, payments, accounting, reports, printing, permissions.
2. **Publishing** to Facebook, WhatsApp, Telegram, Instagram and TikTok.
3. Everything else: chat orders, Bosta, Chatwoot hub, AI agent, Mini App, growth features.

## Sales channels
| Channel | Who | Phase |
|---|---|---|
| Counter (physical) | Walk-in and registered wholesale customers | E |
| Publishing: Facebook, WhatsApp, Telegram, Instagram, TikTok | Public and opted-in audiences | PUB |
| Chat orders (WhatsApp, Instagram, Facebook Messenger) | Resellers | O, then C (human-first) and A (AI) |
| Telegram Mini App | Approved resellers | M |
| TikTok DM | Resellers | G |
| Telegram admin bot | Owner and staff | From PUB |

## Users and roles
`owner`, `manager`, `cashier`, `warehouse`, `accounts`, `payment_reviewer`, `sales`, `catalog_manager`, `integration`. The owner can hold all roles initially. Role matrix in `07-modules-apps.md`; ERPNext role mapping in `05a-erp-configuration.md`.

## Volumes (planning basis)
30–100 chats per day, 20–60 counter invoices per day. Size infrastructure for three times this.

## Languages (DEC-39)
Arabic and English everywhere, **Arabic primary** with RTL. Per-user language; resellers detected per conversation. Full specification in `19-localization-arabic-english.md`.

## Goals
1. A simple, fast ERPNext that staff learn quickly, with unneeded modules and fields hidden.
2. Accurate stock, purchasing, sales, payments, debts and reports in dozens.
3. Fast counter sales by barcode with correct accounting.
4. Add a product once; publish to every channel after one approval.
5. Resellers order through chat with rules enforced in code.
6. AI answers within strict guardrails and hands off cleanly.
7. Correct ERPNext orders and Bosta shipments with no duplicates.
8. One dashboard for the owner and manager.

## Non-goals (v3)
- AI or automation confirming payments, ever.
- Credit or partial payment at the counter (DEC-14).
- Installments in chat or by the AI (staff back-office only).
- Unofficial WhatsApp or TikTok automation that risks accounts.
- A custom accounting or inventory system alongside ERPNext.
- Microservices or Kubernetes.
- A browser-side offline invoice queue at the counter.
- Manufacturing, payroll and HR features.

## Assumptions to confirm (see `12`)
Hardware models, WhatsApp provider, e-invoicing and VAT treatment, tier definitions, cosmetics return policy, purchase flow, account mapping for payment modes.
