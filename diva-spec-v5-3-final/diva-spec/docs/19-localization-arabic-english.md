# 19 Localization: Arabic and English

Every screen, message, printout and document the system produces exists in **Arabic and English**. **Arabic is primary**: it is designed, built and tested first, with right-to-left (RTL) layout. English is a full alternative, not an afterthought (DEC-39).

## 1. Policy
- Language is a per-user setting. Defaults: cashiers, warehouse and accounts staff start in Arabic; owner and manager choose at first login. A language switch is always visible.
- Resellers: the language is detected per conversation, stored as `preferred_language`, and can be switched by the reseller or staff.
- No hard-coded user-facing string anywhere. All text lives in locale files or ERPNext Translation records.

## 2. Surfaces
| Surface | How it is localized | Phase |
|---|---|---|
| ERPNext Desk (kept screens) | Arabic enabled per user with RTL; domain terms and custom labels as Translation records applied by the config script (configuration, not code); untranslated strings found in `E-01` are translated | E |
| POS Next | Arabic UI and RTL verified in `P0-03`; gaps fixed in the patch set (`E-14b`); Arabic item names, scan info card and errors in Arabic | E |
| Diva Ops, Control Room, Mini App | Shared i18n package: i18next with ICU plurals, `dir` and `lang` set on the page, CSS logical properties, mirrored layouts, `ar.json` and `en.json` | E, PUB, M |
| Telegram admin bot | Replies in the user's language; command tokens stay English (`/orders`) with optional Arabic aliases | PUB |
| Customer chat and AI | Reply in the language of the customer's latest message; Egyptian Arabic by default; mixed Arabic and English supported | A |
| WhatsApp templates | Every template exists in `ar` and `en`, approved separately; Arabic primary | PUB, O |
| Receipts, invoices, statements, packing slips | Arabic primary, optional English second line per setting; A4 and 80 mm | E |
| Labels | Arabic name, EAN-13, optional price per dozen; English optional | E |
| Reports and dashboards | Labels and numbers follow the user's language | E, PUB |
| Public posts | Arabic caption first, optional English block per platform; no wholesale price (DEC-10) | PUB |
| Errors, alerts, notifications | Plain-language, in the recipient's language | all |
| SOPs, training, acceptance scripts | Arabic primary with English copies | E |

## 3. Arabic standards
- **Variety:** UI uses clear Modern Standard Arabic with everyday shop words. Customer chat uses Egyptian Arabic. The owner approves the glossary below (OPEN-17).
- **Digits:** Western digits (0–9) by default in both languages, including receipts and barcodes. A user setting can show Arabic-Indic digits (٠–٩). Input fields accept both and normalize to Western (DEC-40, OPEN-16).
- **Currency and dates:** amount then "ج.م" or "EGP" by setting; Gregorian dates, day/month/year; week starts Saturday; time zone Africa/Cairo.
- **Mixed text (bidi):** Arabic names with Latin brands, SKUs or numbers render correctly (`dir="auto"` or isolation). Barcodes, phone numbers and codes are always left-to-right.
- **Fonts:** bundle one Arabic-capable family (for example Noto Sans Arabic, IBM Plex Sans Arabic or Cairo) with a compatible license; no external font CDN at the counter; tested at small sizes on receipts and labels.
- **Plurals:** Arabic has six plural forms; use ICU plural rules, never "add s".
- **Search normalization:** ignore diacritics and tatweel; treat أ إ آ as ا; ى as ي; ة as ه (search only); convert Arabic-Indic digits to Western; search both Arabic and English names; works on either keyboard layout.
- **Shortcuts on the Arabic keyboard layout:** key shortcuts use physical key codes (for example `KeyF` for Ctrl+F), so they work whichever layout is active.
- **No text baked into images:** labels and posts use real text layers. AI-generated images contain no text.

## 4. Product names (DEC-41)
`item_name` in ERPNext is the **Arabic name** (primary). English name, bilingual descriptions and search keywords live in the `Diva Product Rule` doctype owned by `diva_guard` (fields `name_en`, `description_ar`, `description_en`, `keywords`), so no custom fields are added to ERPNext's Item for names (the only Item custom field is the quick-entry barcode, DEC-78). Publishing, chat and the AI use these. Suppliers' English or Chinese names can be stored as keywords.

## 5. Thermal and label printing in Arabic (DEC-42)
Many 80 mm thermal printers do not shape Arabic correctly. In `P0-06` print a test sheet (Arabic text, mixed text, digits, EAN-13) on the real printers. Rule: if the printer cannot do it natively, render the receipt and label as a **raster image** (browser print or QZ Tray raster mode) so shaping and direction are correct. Never ship a receipt that prints reversed or disconnected letters.

## 6. Customer language and AI
- Detect Arabic script, English, and **Franco-Arabic** (Arabic typed in Latin letters, for example "3ayez"). Reply in Arabic script unless the customer clearly prefers English.
- Extraction understands Arabic and Egyptian number words ("اتنين دستة", "تلات دست"), Arabic-Indic digits and common spelling variants.
- Product matching uses Arabic synonyms and the keywords above.
- The evaluation set (`TASK-A-03`) includes dialect, Franco-Arabic, spelling variants and noisy voice transcripts.

## 7. Translation process
1. Source keys in English; Arabic written by a native Egyptian speaker (owner or staff), reviewed in context on staging.
2. Glossary locked before `E-14`.
3. Locale changes go through pull requests. CI fails if any key is missing in `ar` or `en`.
4. Pseudo-localization and RTL screenshot tests for key screens in both languages (Playwright).
5. ERPNext translations are stored as Translation records and applied by the config script.

## 8. Initial glossary (owner approves, OPEN-17)
| English | Arabic | English | Arabic |
|---|---|---|---|
| Dozen | دستة | Piece | قطعة |
| Item | صنف | Barcode | باركود |
| Sales invoice | فاتورة بيع | Purchase invoice | فاتورة شراء |
| Return | مرتجع | Discount | خصم |
| Payment | سداد | Cash | نقدي |
| Bank transfer | تحويل بنكي | Vodafone Cash | فودافون كاش |
| InstaPay | إنستا باي | Customer | عميل |
| Supplier | مورد | Cashier | كاشير |
| Shift | وردية | Stock | مخزون |
| Warehouse | مخزن | Balance | رصيد |
| Outstanding | متبقي | Receipt | إيصال |
| Label | ملصق | Hold sale | تعليق الفاتورة |
| Resume | استئناف | New sale | فاتورة جديدة |
| Manager PIN | رقم المدير السري | Minimum quantity | الحد الأدنى للكمية |

## 9. Tasks (effort about 90 h; range 70–120 h)
| ID | Task | Phase | AC |
|---|---|---|---|
| I18N-01 | Glossary draft, font choice, Arabic printer test sheet | P0 | Glossary reviewed; printers tested (`P0-06`) |
| I18N-02 | ERPNext Arabic baseline: enable for staff, find untranslated strings, Translation records via config script | E | Staff roles see RTL Arabic on every kept screen |
| I18N-03 | Arabic print formats (invoice A4, receipt, statements, payment receipt) | E | Print correctly on real printers |
| I18N-04 | Arabic receipt and label rendering decision and implementation (native or raster) | E | `TEST-68`, `TEST-77` pass |
| I18N-05 | POS Next Arabic and RTL fixes; shortcuts by physical key code; Arabic scan info card | E | `TEST-67`, `TEST-71` pass |
| I18N-06 | Shared i18n package for Ops, Control Room, Mini App; locale CI check | E, PUB | `TEST-73`, `TEST-74` pass |
| I18N-07 | Search normalization service (Arabic variants, digits) in `local-api` and cloud | E | `TEST-69`, `TEST-70` pass |
| I18N-08 | Bilingual product info in `Diva Product Rule` | E | Arabic name primary; English fields editable in Ops |
| I18N-09 | Bilingual publishing captions and WhatsApp template languages | PUB | `TEST-75` passes |
| I18N-10 | Customer language detection, Franco-Arabic, number words, reply language | A | `TEST-76` passes |
| I18N-11 | Arabic SOPs and acceptance scripts with Arabic-UI screenshots | E | Staff complete SOPs in Arabic |

## 10. Tests
`TEST-67` to `TEST-78` in `10-quality-security.md`.
