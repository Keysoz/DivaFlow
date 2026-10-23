# 14 Feature Decision Matrix and Final ERPNext Stack

This file records what we use from **standard ERPNext**, from **POS Next**, and from the **legacy `diva_store` app**, and what we drop. It is the final answer to "which one do we use for what" (DEC-34).

## 1. Final ERPNext stack
| Layer | Choice |
|---|---|
| Core | Standard ERPNext 16, configured only (`05a`), unneeded modules hidden |
| Counter POS | **POS Next by BrainWise** (`pos_next`, GitHub `BrainWise-DEV/POSNext`), pinned version, plus `diva_guard` and a small patch set |
| Staff screens | **Diva Ops** (React PWA served by `local-api`): Receive, Transfer, Count, Labels, Items, Collect, Pack |
| Management | Control Room dashboard (cloud) |
| Legacy `diva_store` | Retired after POS Next cutover; useful logic ported (section 4) |

**Name warning.** There is a different, older app also called "POSNext" (publisher exvas, listed on the Frappe marketplace for ERPNext 14 and 15, MIT). A marketplace review says uninstalling it leaves custom fields behind and can break a site. **Do not install it.** Install only `pos_next` from `https://github.com/BrainWise-DEV/POSNext` (AGPL-3.0, Vue 3, offline-first).

## 2. POS Next: what it gives us (from its published notes; verify in `TASK-P0-03`)
Offline-first selling with automatic sync (the developer says it holds for about a day or until shift close); barcode and keyboard use; shift management with Sales vs Shifts and Payments and Cash Control reports (with bank deposit information); credit sales with settings to allow or block them; paying a customer's receivable account from the POS; offers and promotional schemes with minimum and maximum discount logic; packed items for Product Bundles; item scope by POS Profile; customer group and territory defaults; invoice list with payment mode; offline receipt handling and printing; extension hooks.
**Risks:** the project is young (about 150 stars); its v1.17.0 release notes include a rollback of a change that hid all records, so upgrades can regress; it adds its own custom fields and permission query conditions to ERPNext (vendor-owned; document them and rehearse uninstall); AGPL means a modified fork's source must be available to its users.
**Rules for using it:** pin the exact version; never auto-upgrade; rehearse every upgrade and an uninstall on staging first; keep our patch set small and rebasable; test offline for a full shift (`TEST-53`).

## 3. Feature decisions
### Counter sales
| Feature | Legacy app | POS Next | Decision |
|---|---|---|---|
| Barcode scan adds a line; repeated scan raises quantity | yes | yes (verify) | **POS Next** |
| `qty*barcode` multiplier (for example `5*890…`) | yes | unknown | **Recommended patch** if missing (fast shelf-picking in dozens) |
| Undo last scan (Ctrl+Z) | yes | unknown | Patch candidate, low priority |
| **Scan info card:** name, code, price per dozen and stock shown on every scan | yes (grid and status bar) | unknown | **Required patch** (E-14b) if POS Next does not already show it |
| Hold and resume | yes, buggy | drafts | **POS Next drafts** |
| Customer picker and card (outstanding, limit) | yes | customer dialog, credit info | **POS Next**; patch the card only if too thin |
| **Keyboard shortcuts** (your current map: F1 help, F2 customer, F3 quantity, F4 discount, F5 note, F6 delete line, F7 held sales, F8 payment, F9 print, F10 new sale, Ctrl+F search, Ctrl+Delete clear, Ctrl+Z undo, Ctrl+R return) | yes | built-in shortcuts (map unverified) | **Required patch:** the POS Next keymap is replaced by your current keys, with `preventDefault` in a standalone window, tested on the real keyboard; configurable, with a fallback if a browser blocks a key |
| Command palette (Ctrl+K) | yes | no | Drop |
| Discounts | unlimited, client-trusted | offers, min/max discount | **POS Next offers + `diva_guard`** (5% cashier limit, PIN above, server-side) |
| Payments (cash, non-cash, split, change) | recorded wrongly | yes | **POS Next**; partial and credit blocked at the counter by setting plus `diva_guard` |
| Shift open and close, reconciliation | legacy shift report | shifts, cash control reports | **POS Next** |
| Receipts 80 mm and 58 mm | print formats | printing and offline receipts | **POS Next**; reuse the legacy layout if its default receipt is weaker |
| Returns (Quick Return Ctrl+R) | yes | verify | **POS Next returns**; fall back to standard ERPNext return |
| Low-stock tint on rows | yes | unknown | Optional patch candidate |
| Today's sales widget | yes | reports | Control Room sales page |
| Offline operation | no | yes | **POS Next** (tested) |
| Product bundles (sets) | no | packed items | **POS Next** (when needed) |
| Send invoice by WhatsApp | deferred | not core | Phase G |
| Price check screen | yes | item search shows price | POS Next search; Ops mini screen only if needed |

### Stock and items
| Feature | Legacy | Decision |
|---|---|---|
| Receiving by scan | Stock Entry Material Receipt (no supplier payable) | **Replace:** Ops Receive using Purchase Invoice with Update Stock (DEC-31) |
| Quick Add Item with EAN-13 generation | yes, unvalidated, `ignore_permissions` | **Port** the generator into `local-api` with validation, permissions and tests; keep existing barcodes |
| Barcode label printing | page | **Rebuild** in Ops Labels (EAN-13, dozen and piece) |
| Low-stock alert report and dashboard | report | Standard stock reports with reorder levels; Control Room page; Telegram alert in Phase PUB |
| Transfers and counts | none | Ops (new) |

### Finance and reports
| Feature | Legacy | Decision |
|---|---|---|
| Collect payment with FIFO allocation | page, `ignore_permissions`, no idempotency | **POS Next** pay-on-receivable at the counter; **Ops Collect** for the back office, porting the FIFO idea with permission checks, idempotency and reference fields |
| Customer statement | page | Standard Statement of Account and General Ledger; Ops Collect view; WhatsApp send in Phase G |
| Sales summary, top items, top customers | reports | Standard reports plus Control Room (must reconcile with standard) |
| Profit report (cost from stock ledger) | report | Control Room query, reconciled to standard gross profit |
| Dashboard | Desk page | Control Room |
| Daily server backup script and cron | script | **Reuse the idea** in E-17 with off-site copy and restore test |
| Telegram stock alerts and daily report (backlog) | not built | Phase PUB and Phase G |
| Overdue customer alerts (backlog) | not built | Phase G |

### Dropped
Desk-injected POS (22 JS modules), the CSS that hides Desk elements, the Diva Sale pilot, `Diva POS Settings`, duplicate and `*_old` files, committed build artifacts and the zip inside the package.

## 4. Net effect on the plan
- Counter work shrinks to configure, guard, patch and cut over (`E-14` to `E-14d`).
- We keep our own Receive, Labels, Items, Collect, Transfer, Count and Pack screens because neither app provides them correctly.
- `diva_guard` stays small: server hooks and its own doctypes only.
- Open item: `TASK-P0-03` must answer every "verify" and "unknown" cell above before `E-14` starts.
