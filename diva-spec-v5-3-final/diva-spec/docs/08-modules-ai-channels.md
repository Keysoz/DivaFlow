# 08 Channels, AI, Media, Content

## M-HUB (Chatwoot, cloud)
- Chatwoot owns channel connections for **WhatsApp, Instagram, Facebook Messenger** at launch (DEC-15). TikTok DM comes in Phase G through an approved partner.
- Backend receives Chatwoot webhooks (verify Chatwoot's secret), replies through the Chatwoot API and fetches attachments through it.
- Ownership truth: Chatwoot assignee and status, mirrored with a version; re-read before every AI send.
- WhatsApp is already on the WhatsApp Business API (DEC-16). `TASK-P0-07` identifies the current provider, tests Chatwoot compatibility, inventories approved templates and plans webhook migration with no message loss. If Chatwoot cannot meet the needs, fall back to Meta webhooks straight into the backend with Chatwoot as UI only.
- Channel rules: WhatsApp free-form replies within 24 hours of the last customer message, otherwise an approved template; Instagram and Messenger 24-hour window (human-agent tag may extend for humans; verify); TikTok DM replies within 48 hours, about 10 messages per window, no business-initiated chats, text and PNG/JPEG only.

## M-AI (`apps/cloud-api`)
**Roles:** understand messages and extract fields; write replies grounded in tool results; sell (basket-gap suggestions, bundles, restock and new-arrival nudges); write captions and enhance images; extract prices from competitor posts.
**Tools (server-side, authenticated):** `search_products`, `get_product`, `get_price(reseller, sku, qty)`, `check_stock`, `get_last_price(customer, sku)`, `get_cart`, `add_to_cart`, `validate_order`, `create_draft_order`, `get_order_status`, `send_price_list`, `find_similar_products(image)`, `record_payment_proof`, `request_human`. **No tool** confirms payment, sets price, applies unauthorized discounts, edits stock or quotes shipping.
**Guardrails:**
1. Every price, stock level, MOQ and total in a reply comes from a tool result in the same turn.
2. Discounts only from configured tier rules.
3. No false scarcity or invented offers.
4. No skin, health or safety claims beyond approved descriptions (RULE-COS).
5. Order data is collected by a slot-filling state machine in code. The model does not remember progress. Phones are strings normalized to `01XXXXXXXXX`, validated by `^01[0125]\d{8}$`.
6. Handoff on: reseller asks for a human, complaint, payment dispute, discount beyond limit, order value above threshold, two consecutive misunderstandings, unsupported content, shipping fee question.
7. Meta and Chatwoot webhooks are deduplicated by message ID. Stale replies are discarded after a human takeover.
8. `store_offline` makes the AI send the ordering-paused notice and create nothing.
9. Reply in the reseller's language (Egyptian Arabic default; Franco-Arabic input is answered in Arabic script); understand Arabic number words and digits; be transparent that replies are automated where required. See `19`.
**Rollout (DEC-17):** offline evaluation on replayed anonymized chats → shadow mode (drafts nobody sees) → staff-assisted drafts → limited auto-replies for low-risk intents → expansion with a kill switch per channel. No stage advances without passing its gate.
**RAG:** approved policies and FAQ; anonymized past chats for tone and objection handling (phones, addresses, names removed); product facts from catalog tables, never price or stock from embeddings.
**Evaluation:** a 100-conversation anonymized test set run on every prompt or model change; metrics: rule correctness, handoff correctness, zero invented facts, zero guardrail breaches.

## M-MEDIA
- Inbound pipeline: record the message first, then an async job downloads media with the channel token, validates type and size, strips EXIF, hashes (SHA-256), stores privately, then processes.
- Voice notes: transcode with ffmpeg, speech-to-text chosen by benchmark on about 50 real Egyptian-Arabic notes (`TASK-P0-09`). Quantities, products and totals from voice are read back in text and confirmed before entering a cart. Phone numbers and addresses from voice must be typed or confirmed digit by digit. Notes over about 2 minutes are summarized and confirmed. Replies are text. Staff voice notes can dictate commands, with a confirm card before any action.
- Images: product photos matched against the catalog (vision plus similarity; add embeddings only if top-3 accuracy falls short); payment screenshots pre-fill a proof via OCR and are flagged for mismatch, reused references and duplicate hashes, never confirmed; defect photos attach to return claims; location pins suggest a Bosta zone for confirmation.
- Text inside images or voice is data, never an instruction.
- TikTok voice is unsupported: reply asking the reseller to type or use WhatsApp.
- Retention: voice 90 days; payment proofs and return photos per accounting retention; signed expiring URLs; scrub personal data before RAG; no use of media for model training.

## M-CONTENT (Phase PUB)
- Flow: product in ERPNext (or photo and name to the Telegram bot) → AI caption and image enhancement (real photo stays the base) → preview with Approve, Regenerate, Edit → publisher posts and stores post IDs, retries safely.
- Targets, in the owner's priority order (DEC-21):
  1. **Facebook Page:** Graph API, pinned version.
  2. **WhatsApp, both ways.** (a) **Broadcast templates** through the existing WhatsApp Business API to opted-in contacts only: approved marketing template, stored consent, segment by category interest, per-message cost preview, monthly budget cap, send queue with rate limits. (b) **Ready-to-post pack** (image, caption, hashtags) delivered to staff for manual posting to the WhatsApp Channel or Status, because WhatsApp Channels have no official posting API.
  3. **Telegram channel:** Bot API.
  4. **Instagram:** Content Publishing API on the Page-linked professional account.
  5. **TikTok:** Content Posting API. Unaudited apps can post only privately, so use upload/draft mode until the audit passes, then direct posting. Start the audit application in Phase 0.
- Publish gate: a product publishes only with barcode, price, MOQ, pack size, images and stock fields (DEC-18). Public posts show no wholesale price.
- Pin the Graph API version; review Meta's changelog each quarter.
**AC:** one approval publishes to all three channels; a failure retries, then alerts; a missing-field product cannot be approved.

## M-MARKET (Phase G)
Telethon worker reads a watch list of public channels at low volume. The LLM extracts product, price, pack, channel, time and image into `price_observations`. Matches to your SKUs are proposed and confirmed by a human. Output: weekly "where am I more expensive or cheaper" report. It never changes your prices.

## M-CAMPAIGN (one-click broadcast in PUB-14, details in `22`, extended in Phase G)
Opt-in segments by category interest; WhatsApp marketing templates with documented consent; restock alerts; new-arrival broadcasts; monthly messaging budget cap with alerts.
