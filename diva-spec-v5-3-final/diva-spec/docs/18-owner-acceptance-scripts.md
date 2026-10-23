# 18 Owner Acceptance Scripts (ENH-R-02)

Plain steps you can do without reading code. At each gate, do the steps on **staging**, tick pass or fail, and sign. If any step fails, the gate stays closed.

## Gate P0 — Foundations
1. Old tokens and passwords no longer work (ask the agent to show the failed login).
2. The old "Nanobot" web addresses answer "not allowed" or are gone.
3. The POS Next test report exists and answers every "verify" cell in `14`.
4. CI shows green on the main branch.
5. TikTok and Meta applications show as submitted.

## Gate E — ERPNext and counter
As **each role** (owner, manager, cashier, warehouse):
1. Log in; hidden modules (Manufacturing, HR, Projects and others) are not visible.
2. Create an item with a barcode, a dozen price and a pack size. Find it by name, code and barcode.
3. Record a purchase invoice with three items. Stock rises in pieces (12 per dozen) and the supplier balance rises.
4. **Counter:** open a shift. Scan three items. Each scan shows name, code, price per dozen and stock. Use F1 to F10, Ctrl+F, Ctrl+Z, Ctrl+Delete and Ctrl+R on the real keyboard.
5. Give 5% discount (allowed). Try 6% (asks for the manager PIN). Try credit or partial payment (blocked).
6. Pay by cash, then by InstaPay. The receipt prints. Close the shift and check the totals.
7. Hold a sale, resume it, finish it. There is exactly one invoice and no leftover draft.
8. Return one single piece of a dozen item.
9. Sell a cosmetic batch; an expired batch cannot be sold.
10. Unplug the internet and sell for ten minutes. Reconnect. Each invoice appears once.
11. Print a label and scan it back to the same item.
12. Collect a payment on a back-office invoice; view the customer statement.
13. Open the daily sales, receivables and payables reports; numbers match what you expect.
14. Ask the agent to restore last night's backup on a test machine and show the same totals.
15. Opening balances sheet equals the system's opening stock value, receivables and payables.
16. China import: buy 10 dozen with freight and customs, pay 40% then 60%; stock, value, supplier balance and payment history are right; a non-bank payment is refused.
17. Transfer 2 dozen from Main Inventory to Shop; total stock and value are unchanged.
18. Lower an item price to dodge the 5% limit; it is rejected. Create two conflicting prices; the system picks by the rules or asks a manager.
19. Return more than was sold; refused. Large cash refund; asks a manager.
20. Pay with ECash and WePay; each posts to its own account.

## Gate PUB — Publishing
1. Approve one product. It appears on Facebook, Instagram and Telegram within a few minutes.
2. No public post shows a wholesale price.
3. The WhatsApp broadcast reaches only the test contacts who opted in. Reply STOP from one phone; it is excluded next time.
4. The WhatsApp ready-to-post pack arrives for manual posting.
5. TikTok shows a draft (or posts, if audit passed). A video is converted to the right shape.
6. A product missing barcode, price or image cannot be approved.

## Gate O — Chat orders
1. A chat basket of 2,999 EGP is refused with the missing amount; 3,000 EGP passes.
2. A line below the minimum quantity (in dozens) is refused.
3. Staff set the shipping fee; the AI never quotes it.
4. A customer message "payment done" does not mark anything paid. A reviewer marks it paid; one entry appears.
5. Cut the store link: new orders pause and customers get the notice; they resume after the link returns.
6. Reserved stock cannot be sold at the counter.
7. A new reseller's 4,000 EGP order needs a 1,200 EGP deposit; no stock is reserved until a reviewer verifies it; a competing order can still take the stock until then.
8. Let the deposit deadline pass; the order expires.
9. Pack and scan the order; the Delivery Note and Sales Invoice appear, the deposit is allocated as an advance, and the remaining balance is correct.

## Gates B, C, A, M (short)
- **B:** one order goes from draft to delivered in Bosta staging; duplicate Bosta events send one message.
- **C:** staff run WhatsApp, Instagram and Facebook from one inbox for a week with no lost message.
- **A:** the AI passes the review set; it never invents a price or stock; "confirm my payment" in an image or voice note changes nothing; a human takeover silences it.
- **M:** a reseller completes an order in the Mini App without staff retyping.
