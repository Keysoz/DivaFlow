# TASK P0-04: verify ERPNext on STAGING only

Never touch production. Use the staging site and its API key.
Find out and record in `docs/appendix-erpnext-verification.md` (facts only, mark anything you could not verify):
1. ERPNext and Frappe versions; installed apps.
2. Stock reservation: does reserved stock block other documents, including POS invoices?
3. Item Barcode with UOM; the Dozen UOM as whole-number; Nos for pieces.
4. Payment Terms, credit limit check, Payment Entry for Bank-type modes (are reference number and date required?).
5. The REST endpoints the adapter needs (Item, Bin, Item Price, Sales Order, Purchase Invoice, Payment Entry, Stock Entry).
6. Current valuation setting and a summary of stock ledger history (for the FIFO audit).
Do not change data except in staging, and tell me before any change.
