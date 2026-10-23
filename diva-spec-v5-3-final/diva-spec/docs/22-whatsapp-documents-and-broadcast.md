# 22 WhatsApp: Send Invoices, and One-Click Broadcast

## 1. Send invoices and documents by WhatsApp (DEC-58)
Besides printing, staff can send a **Sales Invoice, Purchase Invoice, payment receipt or statement** to the customer or supplier on WhatsApp. Two levels:

**Level 1 (Phase E, free, no cloud needed).** The Ops **Invoices** screen and a POS Next button show **Print**, **Download PDF** and **Open in WhatsApp**. Open in WhatsApp is a `wa.me` link with the normalized number and a ready message in Arabic or English; staff attach the downloaded PDF. It works whenever the store network works and costs nothing.

**Level 2 (Phase PUB, one click).** **Send via WhatsApp** sends the PDF automatically through the WhatsApp Business API.
1. Staff click Send. `local-api` creates the PDF from ERPNext using the Arabic right-to-left print format.
2. The request goes into the local outbox and then to `cloud-api` with an idempotency key (document name, version hash, recipient).
3. `cloud-api` uploads the PDF as WhatsApp media and sends an **approved utility template with a document header**. The PDF is never a public link.
4. Delivery webhooks update the status: queued, sent, delivered, read, failed. Ops and the Control Room show it. A failure shows the Level 1 fallback.
5. If the internet is down, the request waits in the outbox and sends when it returns. Level 1 still works.

**Templates** (category utility; Arabic primary, English second): `invoice_ready` (customer name, invoice number, total, balance due, document), `purchase_invoice_copy` (for suppliers), `payment_receipt`, `statement`. Keep them transactional. Never add offers: Meta may reclassify the template as marketing, which costs about 18 times more.

**Rules**
- Send only to numbers with recorded consent for transactional WhatsApp (captured when the customer or supplier is created or at the first chat). Normalize the phone number.
- One send per document version; a resend needs a deliberate click.
- Per-customer setting "send invoice automatically on submit" for repeat resellers (default off).
- Suppliers: send only when they use WhatsApp (China suppliers are usually not required).
- Show the cost estimate in Settings, not on every click.

**Cost (Meta, Egypt, from 1 October 2026):** a utility message is $0.0036 (about 0.19 EGP), possibly plus 14% VAT. 1,000 invoices cost about $3.60. A service reply inside an open 24-hour window is also $0.0036 after the first 1,000 per number each month.

### 1a. Customers message first: the cheapest valid path (DEC-64)
WhatsApp lets you reply to a customer freely, including with a PDF, for 24 hours after **they** message you. Sending after that window needs an approved template. So:
1. **Put a "Message us" link and QR** (`wa.me/<number>?text=...`) on receipts, invoices, statements, the shop sign and your public posts (`ENH-C-09`). A customer who scans it messages the shop first and opens the window.
2. **Choose the path automatically when staff click Send via WhatsApp:** (a) the customer's window is open: send the document as a normal reply (service message; the first 1,000 per number each month are free, then the utility rate); (b) the window is closed and consent exists: send the approved utility template; (c) otherwise show the free manual link from Level 1.
3. **Verify a reseller's phone by their first inbound message** (it proves they control the number), with staff confirmation. No paid verification template is used.
Savings are small for invoices (about $0.0036 each) but this also avoids verification fees and keeps follow-ups inside the window.

## 2. One-click broadcast to all customers (DEC-59)
**Is WhatsApp the cheapest way? No.** A WhatsApp marketing message to Egypt costs **$0.0644** (about 3.4 EGP, possibly plus 14% VAT) with no volume discount, so 500 customers cost about $32 per broadcast. It is the only way to reach every customer reliably in one click, so we build it, but with free options first.

Control Room, **Broadcast** page:
1. Write the message or pick an approved template (Arabic and English).
2. Choose the audience: all opted-in customers, or a segment (category interest, tier, last purchase date).
3. See the recipient count and the **cost**, then confirm.
4. Send. Results show delivered, failed and STOP replies.

**Channels, cheapest first**
| Channel | Cost | Reach |
|---|---|---|
| Telegram channel or bot subscribers | Free | Customers who joined |
| WhatsApp Channel or Status (ready-to-post pack, posted by staff) | Free | Followers only; manual |
| WhatsApp marketing template to opted-in customers | $0.0644 per delivered message | Every opted-in customer |

Default policy: send ordinary offers on the free channels first; use the paid WhatsApp broadcast for important announcements and targeted segments. The monthly spend cap exists but is off for now (DEC-33).

**Opt-in is required.** Meta's rules require opt-in for business-initiated marketing messages. Capture consent at the counter (a checkbox when creating a customer), at the first chat, and by a START keyword. Store proof (who, when, source). Honor STOP immediately. Only opted-in contacts are ever included; the page never offers "everyone" beyond that.

## 3. Data additions
`message_consents` (party, channel, category transactional or marketing, source, time, revoked time); `outbound_documents` (document type and name, version hash, recipient, status, provider message ID); `broadcasts` and `broadcast_recipients` (message, audience, cost estimate, status per recipient).

## 4. Tasks
| ID | Task | Phase |
|---|---|---|
| E-18 | Level 1 invoice sharing: Print, Download PDF, Open in WhatsApp in Ops Invoices and POS Next | E |
| PUB-13 | Level 2 one-click send with utility templates, outbox, status tracking, fallback | PUB |
| PUB-14 | One-click broadcast page with audience, cost preview, confirmation, free channels first, consent and STOP handling | PUB |
Effort about 50–90 h in total.

## 5. Tests
`TEST-92` to `TEST-100` in `10-quality-security.md`.
