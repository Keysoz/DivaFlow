# diva_desk

Thin client-side Desk layer for the Diva workflows:

- Purchase Receipt: focus supplier, Add New Item dialog, EAN-13 generation, label print.
- Sales Invoice: focus customer, Pay (full/partial, Cash default), Print after submit/pay.
- Global search (`Ctrl+K`) for Items (code/name/group/barcode), Customers/Suppliers (id/name/phone) and Sales Invoices.
- POS-Next-style shortcuts (`F1`, `F2`, `F3`, `F8`, `F9`, `Ctrl+S`, `Ctrl+Enter`).

Server methods live in `diva_guard`; this app contains only Desk client code and the Diva report print helper.
