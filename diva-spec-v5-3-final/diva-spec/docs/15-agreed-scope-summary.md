# 15 Agreed Scope Summary (plain language)

What the owner and the specification have agreed will be done, what will not, and what depends on a test. If this file and another file disagree, tell the owner and fix this file.

## 1. Will be done
| Area | What | Phase |
|---|---|---|
| ERPNext simplification | Unneeded modules hidden (Manufacturing, HR and Payroll, Projects, Quality, Assets, CRM, Website, Support). Item, Sales Invoice, Purchase Invoice, Customer, Supplier and stock forms simplified by hiding fields, setting defaults and tightening permissions. Nothing is deleted or uninstalled. Applied by a repeatable configuration script after a field-by-field review of the live site | E |
| Units | Stock in pieces; buying, selling and prices in dozens (1 dozen = 12 pieces) | E |
| Purchasing | Purchase Invoice with Update Stock (goods and invoice arrive together); supplier payables and payments | E |
| Money | Payment modes Cash, Bank Transfer, Vodafone Cash, InstaPay; no VAT, no e-invoicing; expenses and cash tracking | E |
| Counter | POS Next (BrainWise) with a small guard app and a few patches: held sales, shifts, receipts, offline selling, returns | E |
| Counter look and feel | **Scan info card** (name, code, price per dozen, stock) on every scan and **your current keys** (F1 help, F2 customer, F3 quantity, F4 discount, F5 note, F6 delete line, F7 held sales, F8 payment, F9 print, F10 new sale, Ctrl+F search, Ctrl+Delete clear, Ctrl+Z undo, Ctrl+R return) | E |
| Counter rules (enforced on the server) | Minimum quantity in dozens; cashier discount up to 5%, manager PIN above; price must match the price list; no credit or partial payment at the counter | E |
| Staff screens | Diva Ops: Receive (Purchase Invoice), Transfer, Count, Labels (EAN-13), Items and barcodes, Collect, Pack | E |
| Barcodes | Existing internal EAN-13 barcodes kept; generator ported with validation | E |
| Brand | "Diva Navy and Gold" design tokens (`packages/ui/tokens.css` and `tokens.json`, light and dark) with a WCAG AA contrast test; locally bundled IBM Plex Sans Arabic; the Diva look on Ops, Control Room, Mini App, POS Next, receipts, labels and prints; ERPNext Desk stays stock with only the logo and app name set by config | E |
| Cosmetics | Batch and expiry tracking, first-expiry-first-out, expired stock blocked | E |
| Old app | Reviewed; retired after POS Next works; useful logic ported | E |
| Publishing | Facebook, WhatsApp (broadcast templates and a manual pack), Telegram, Instagram, TikTok | PUB |
| Chat orders | Minimum 3,000 EGP, minimum quantities, shipping fee set by staff, chat stock reservations, payment proof reviewed by a person, link-down pause | O |
| Later phases | Bosta (B), chat inbox (C), AI agent with voice and images (A), Telegram Mini App (M), growth (G) | in that order |
| Safety | Exposed credentials rotated first; no automation ever confirms a payment; no wholesale prices in public posts | P0 and all |

## 2. Will not be done
- A new custom ERPNext app beyond the small guard app, or custom fields of our own.
- A Desk theme app in production (the ERPNext Desk stays stock; a dev-only trial is optional and never ships).
- Keeping the old Desk POS or the Diva Sale pilot.
- Credit, partial payment or installments at the counter or in chat.
- Automatic payment confirmation by the AI or any workflow.
- VAT or e-invoice features.
- Command palette (Ctrl+K).
- Posting to WhatsApp Channels by unofficial tools (a manual ready-to-post pack is provided).
- TikTok direct posting before TikTok approves the app; TikTok voice messages.
- A broadcast budget cap for now (the setting exists, off).
- Starting Bosta, chat inbox, AI or Mini App before ERPNext and publishing are finished.
- Manufacturing, payroll and HR features.

## 3d. Cost savings adopted (v5.3)
Small cloud server first; "Message us" QR so customers message first and invoices go by the cheapest valid WhatsApp path; fixed logic for routine questions; small AI model first; self-hosted monitoring; media and backups on R2 or B2. Not adopted: dropping n8n; replacing AI backgrounds.

## 3c. Added in v5.0 (2026-10-21)
Send invoices, purchase invoices, receipts and statements to customers and suppliers on WhatsApp besides printing (free link in Phase E, one-click send in Phase PUB, about 0.19 EGP per message); one-click broadcast with a cost preview and free channels first (WhatsApp marketing is about 3.4 EGP per message, so not the cheapest); a model assigned to every job in `opencode.json`.

## 3b. Added in v4.1 (2026-10-20)
China import purchasing (purchase order, partial receipts, landed costs, foreign currency, advances, bank-only); six payment modes (adds ECash and WePay); Gallery warehouse; 30% deposit for new resellers with stock reserved only after verification; invoice and delivery at ready-for-dispatch; FIFO costing; effective-discount and price-conflict enforcement; stricter employee returns; manual couriers. **Not adopted:** Telegram-first ordering and a website storefront (deferred), keeping the old app.

## 3a. Languages
Everything in Arabic and English; Arabic primary with right-to-left layout. Covers ERPNext screens, POS, Ops, dashboard, Mini App, Telegram bot, receipts, invoices, labels, WhatsApp templates, public posts, AI replies (Egyptian Arabic and Franco-Arabic understood) and SOPs. Western digits by default. See `19`.

## 3. Accepted enhancements (53 items, `16`)
All P0 items and 30 chosen P1 items: onboarding package and acceptance scripts; opening balances and a simple chart of accounts; write-offs; manager PIN security; offline-sync alerts; data quality dashboard; accountant monthly pack, wallet reconciliation, price rounding, petty cash and bulk price updates; cash drawer, receipt branding, cycle counts, near-expiry alerts; Telegram photo-to-item intake; content calendar, click-to-chat attribution, image standards, WhatsApp opt-out, TikTok media pipeline, brand voice and cosmetics-claims checks; price-list export and pickup orders; unknown-contact screening, canned replies, after-hours handling; AI review queue, handoff summaries, cost caps and order-status replies; security scanning, secrets manager, edge protection, uptime checks, recovery drills; reseller terms and privacy notice; KPI dashboard and weekly owner summary. Deferred: 25 items (mostly P2).

## 4. Depends on the Phase 0 POS Next fit test
Scan info card and the key map as patches (expected to be possible); the `qty*barcode` shortcut, undo last scan and low-stock tint (added if missing); compatibility with ERPNext 16; a full offline shift; dozen and piece handling. If POS Next cannot meet these with small patches, the counter screen is built in Diva Ops instead.
