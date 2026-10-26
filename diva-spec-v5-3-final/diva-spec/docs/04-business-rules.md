# 04 Business Rules

All rules are implemented once in `packages/rules-engine` as pure functions with unit tests. Rules read configuration from versioned Settings (`rule_set_version`). Failures return structured errors, for example `{"rule":"min_total","required":3000,"current":2550,"gap":450}`.

## RULE-UOM (DEC-20)
1. Stock UOM is **Nos** (piece). **Dozen** is a UOM with conversion 12. Purchase UOM and Sales UOM are Dozen. Item prices are per Dozen.
2. Sales and purchases are entered in whole dozens (the Dozen UOM is configured as whole-number). Piece-level quantities (returns of single defective pieces, counts, adjustments) use Nos.
3. A dozen barcode carries UOM Dozen; a piece barcode carries UOM Nos. Scanning a dozen barcode adds 1 Dozen.
4. `min_qty`, `qty_step`, MOQ and `max_qty` are expressed in dozens.
5. Reports show dozens for trading and pieces for stock counts. Never mix without stating the unit.

## RULE-MOQ (DEC-07)
1. Each product has `min_qty` and `qty_step` (pack size) in `product_rules`. MOQ scope is the product family with an optional per-variant override.
2. A line must satisfy `min_qty` and be a multiple of `qty_step`, both in dozens (RULE-UOM).
3. **Applies to chat orders and counter sales.**

## RULE-MIN (DEC-07)
1. `goods_subtotal` (authoritative prices, after line discounts, before shipping) must be at least `MIN_ORDER_TOTAL_EGP` (default 3000).
2. **Applies to chat orders only.** It does not apply at the counter.
3. When short, return the gap and suggest items that fit it (best sellers, same category, previously bought).

## RULE-PRICE
1. Price source order: customer-specific price list, then the reseller's tier price list, then the standard list. ERPNext's pricing engine computes it.
2. Prices are fetched at validation and at confirmation. Cart prices are display only.
3. A price snapshot is stored when the order is confirmed. A price that changed during checkout is shown and reconfirmed.
4a. **Conflicts are resolved deterministically (DEC-51):** a valid approved customer-specific price beats the customer-group price list, which beats the channel default list. Expiry dates and quantity breaks are honored. If two rules at the same level still conflict, the sale is blocked for manager review. The price source used is logged on the line.
4. The last price sold to the customer for the item is shown to cashiers and available to the AI as a tool result.
5. Public posts never show wholesale prices; they show MOQ and "reseller price in catalog or chat" (DEC-10).

## RULE-DISC (DEC-13)
| Role | Maximum discount without approval |
|---|---|
| cashier | 5% |
| manager | configurable, default 15% |
| owner | unlimited |
**The limit applies to the effective discount (DEC-50):** (price-list subtotal minus net subtotal) divided by price-list subtotal, so lowering an item rate or stacking line and invoice discounts cannot bypass it. It is enforced on the server for POS and standard invoices, whatever the source. Above a role's limit needs a manager PIN (or owner PIN). Each discount and price override stores actor, reason, amount and approver in `override_audit`, and triggers an owner alert above a configured threshold. The AI may offer only discounts allowed by tier rules (`max_discount_pct` per tier); code enforces it.

## RULE-CREDIT (DEC-14)
1. **No credit and no partial payment at the counter.** Counter sales are paid in full (cash or non-cash).
2. Credit and installments exist only as back-office invoices created by the manager for approved resellers with an ERPNext credit limit, using Payment Terms Templates. The AI and chat checkout never offer them.
3. ERPNext's credit limit check is the enforcement point. Exceeding needs an owner override, logged.

## RULE-PAY
1. No automation or AI may verify a payment. A customer message or screenshot only creates a `payment_proofs` record (method, claimed amount, reference, image hash) and notifies staff.
2. A user with `payment_reviewer` verifies in the Control Room. Verification writes the ledger, then the gateway creates a **draft** Payment Entry. An authorized user submits it in Ops.
3. Methods: Cash, Vodafone Cash, InstaPay, bank transfer, COD (chat orders only, per payment policy).
4. Payment policy per reseller: `deposit_30` (default for **new resellers**: 30% of the eligible goods subtotal after discounts, excluding shipping and taxes), `prepaid_only`, `cod_allowed`. COD unlocks after 3 completed orders with no disputes (configurable). A deposit is recorded as a **customer advance** (Payment Entry against the Sales Order), never as sales revenue, and is allocated to the Sales Invoice at ready-for-dispatch. Example: goods subtotal 4,000 EGP gives a 1,200 EGP deposit and 2,800 EGP goods balance, plus the staff-set shipping fee (DEC-44).
5. The ledger is append-only. Corrections are new entries.
6. Flag proofs with mismatched amount, reused reference or duplicate image hash.

## RULE-SHIP (DEC-12)
1. Shipping fee is decided **per order by staff**. The AI never quotes shipping.
2. A validated chat order moves to `awaiting_shipping_quote`. Staff set the fee, then the final total is sent for reseller confirmation.
3. Shipping is excluded from the 3,000 EGP minimum and included in the COD amount.
4. COD amount equals the order total minus verified prepaid amount.
5. Addresses resolve to Bosta city/zone/district IDs and are confirmed with the reseller before shipment creation.

## RULE-STOCK (DEC-08)
1. Available-to-promise equals ERPNext actual stock in sellable warehouses minus reservations.
2. **Chat reservations are protected, and they follow the payment policy (DEC-44).** For `deposit_30` and `prepaid_only`, stock is reserved **only after a reviewer verifies the required payment**; the Sales Order is then submitted with reservation. For `cod_allowed`, stock is reserved at reseller confirmation. An order that is merely submitted never holds stock. Competing orders cannot reserve the same available stock. The counter cannot sell reserved stock.
3. An order waiting for its deposit expires at the **deposit deadline** (default 24 hours, configurable, OPEN-19). A reserved order cancelled or expired releases its stock. A job does this and logs it. Refunds and changes after reservation need an authorized user.
4. Negative stock is disabled. Out-of-stock items are rejected, with an opt-in restock alert.
5. Phase 0 verifies native reservation behavior (`TASK-P0-04`). If native reservation does not block the counter, use a backend hold table checked at the gateway and never describe it as guaranteed.
6. Warehouses (DEC-49): Main Inventory, Shop (the counter), Gallery, Returns and Defects (not sellable), In Transit. Only warehouses flagged sellable count. Whether Gallery is sellable and which warehouses feed chat availability is OPEN-20 (default: Main Inventory and Shop count for chat; Gallery is display only).

## RULE-COS (cosmetics)
1. Cosmetic items track batch and expiry. Picking follows first-expiry-first-out.
2. Expired batches cannot be sold. A near-expiry report runs at a configurable threshold (default 90 days).
3. Makeup shades are variants; MOQ per family unless overridden.
4. The AI makes no skin, health or safety claims beyond approved product descriptions.

## RULE-RET (DEC-52)
1. Returns use ERPNext return documents and credit notes. Employees may process them within limits; they cannot cancel invoices or issue arbitrary refunds.
2. A return needs a valid original sale (or an approved return reference). The returned quantity cannot exceed the quantity sold minus earlier returns. The return window is 14 days from delivery (OPEN-21). A reason is mandatory. The employee and times are recorded.
3. Refunds go to the original payment method where feasible. Refunds are capped at the invoice/return total — full or partial, cumulative per invoice (OPEN-21, closed 2026-10-26). **Manager approval** is required for returns without a valid reference and policy exceptions.
4. Returned goods go to the Returns and Defects warehouse and become sellable only after assessment and a transfer.
5. Opened cosmetics: OPEN-04.

## RULE-IDENTITY (DEC-64)
A channel identity (WhatsApp number, Instagram ID, Telegram ID) is linked to a reseller when the reseller messages the shop first from that identity and staff confirm. No paid verification template. Never merge identities by display name.

## RULE-AUDIT
Every price change, discount, override, approval, payment decision, setting change, pause, export and role change is audited with actor, time, old and new values.

## RULE-RULESET
Settings (minimum total, MOQ defaults, tiers, discount limits, payment policies, reservation expiry, handoff thresholds, templates, working hours) are versioned with an effective date. Each order stores the `rule_set_version` it was confirmed under.

## RULE-COST (DEC-45)
Inventory valuation is **FIFO**. Before enabling it in production, audit the site's current valuation setting, stock ledger and opening quantities and values on a staging copy; never switch blindly or edit the ledger by hand; reconcile with the accountant. Opening stock is loaded with real costs.

## RULE-TAX (DEC-26)
The shop charges no VAT and issues no e-invoices. Tax templates stay empty and tax fields are hidden. Revisit if obligations change.

## RULE-PUR (purchasing)
1. You buy from traders in dozens. Buying prices are per dozen.
2. **Local purchases (DEC-31, DEC-47):** goods and supplier invoices arrive together, so use Purchase Invoice with Update Stock. **China imports:** Purchase Order, then one or more Purchase Receipts (ordered, shipped and received quantities, discrepancies), then Purchase Invoice with a Landed Cost Voucher for freight, insurance, customs and clearance; the supplier currency and agreed exchange rate are recorded; advances paid before the invoice are allocated to it; **bank transfer only**. Never double-count stock. For local purchases: Purchase Receipt is not used unless this changes. Stock Entry (Material Receipt) is only for opening stock and non-purchase stock, because it creates no supplier payable. Never create two stock movements for one delivery.
3. Supplier invoice numbers are checked for uniqueness per supplier (Accounts Settings option).
4. Supplier payables come only from the general ledger. No custom debt ledger.
5. Landed costs are recorded when they exist so margin reports use real cost.

## RULE-ACCT (accounting and payments)
1. Customer and supplier balances come from ERPNext's general ledger, never from a custom counter.
2. An invoice is paid only through a recorded payment (Payment Entry or POS payment). Never mark paid without it.
3. Modes of Payment (DEC-48): Cash, Bank Transfer, Vodafone Cash, InstaPay, ECash, WePay, each mapped to its own account (OPEN-10). Rename the legacy E-Wallet mode to Vodafone Cash and add Bank Transfer.
4. Expenses are recorded through standard Payment Entry or Journal Entry with an expense account, by authorized roles only. Sales revenue, cash received and expenses are reported separately.
5. Submitted documents are never deleted. Corrections use returns, credit notes or cancellation with permission.
6. Fiscal years, valuation method and company defaults are not changed casually; assess impact on existing transactions first.
