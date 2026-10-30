# 27 Brand and Design Tokens

This document is the **single source of truth** for the Diva visual identity: the logo, the color palette named **"Diva Navy and Gold"**, the type and spacing scale, and the rules that keep every surface consistent. It applies to Diva Ops, Control Room, the Mini App, POS Next theming, receipts, labels, invoices and publishing templates. Implementation is tracked as tasks **BRAND-01** to **BRAND-05** (see `docs/09-build-plan.md`). The choices behind it are recorded as **DEC-92**, **DEC-93** and **DEC-94** (see `docs/12-decisions-open-items.md`). The outstanding logo deliverable is tracked as **OPEN-22**.

## 1. Brand source

- The owner's logo is `assets/brand/logo-original.jpg`: a warm cream background (#EDE7DB), a near-black thin-serif "DS" monogram in a circle with "DIVA STORE" beneath.
- The cream background is baked into the JPEG. In the navy theme, show the logo on a cream rounded badge instead of cutting it out.
- The owner will supply a transparent SVG or PNG, and ideally a gold-on-navy and a white version for dark headers. Track this in OPEN-22.
- Until then: use the original JPEG on a cream badge; never recolor the raster logo.

## 2. Palette "Diva Navy and Gold"

All colors below are **design tokens**. Nothing in any app hard-codes a color value; every color reference goes through the tokens (see section 5).

### Light mode

| Token | Value | Use |
|---|---|---|
| `page` | #F4F6F8 | Page background |
| `panel` | #FFFFFF | Panels and cards |
| `text` | #14233A | Primary text |
| `primary` | #1F3A5F | Primary buttons and links (white text on it) |
| `on-primary` | #FFFFFF | Text on the primary button |
| `text-secondary` | #4A5A70 | Secondary text |
| `border` | #D9DEE6 | Decorative lines only |
| `gold` | #C9A24B | Highlights, active-tab underline, badges; never text on light backgrounds |
| `on-gold` | #14233A | Text on a gold button |
| `success` | #1F7A6D | Success states |
| `warning` | #9A6208 | Warning states |
| `error` | #A8281F | Error states |

### Dark mode

| Token | Value | Use |
|---|---|---|
| `page` | #0F1B2D | Page background |
| `panel` | #16263D | Panels and cards |
| `text` | #EAEFF6 | Primary text |
| `text-secondary` | #A9B6C9 | Secondary text |
| `primary` | #D6B25E | Primary button (gold) |
| `on-primary` | #0F1B2D | Text on the gold primary button |
| `on-gold` | #0F1B2D | Text on a gold button |
| `gold` | #D6B25E | Gold accent |
| `success` | #6FD0BB | Success states |
| `warning` | #E6B45A | Warning states |
| `error` | #F09A92 | Error states |
| `border` | #2A3B55 | Decorative lines only |

### Measured contrast (WCAG)

Light mode:

| Pair | Ratio | AA |
|---|---|---|
| text on page | 14.6 | pass |
| text on panel | 15.8 | pass |
| secondary on page | 6.5 | pass |
| white on navy button | 11.5 | pass |
| navy text on gold button | 6.6 | pass |
| gold on navy | 4.8 | pass |
| success on page | 4.8 | pass |
| warning on page | 4.7 | pass |
| error on page | 6.5 | pass |

Dark mode:

| Pair | Ratio | AA |
|---|---|---|
| text on page | 15.0 | pass |
| secondary on page | 8.4 | pass |
| gold on page | 8.6 | pass |
| success on page | 9.4 | pass |
| warning on page | 9.1 | pass |
| error on page | 8.0 | pass |

**Warning:** accent gold #C9A24B on the light page background is only **2.2:1**. On light backgrounds the gold token is **decorative only** — highlights, underlines, badges with non-text use — and is **never used for text on a light background**. Normal text everywhere must be at least **4.5:1**.

## 3. Typography

- **IBM Plex Sans Arabic** for both Arabic and Latin in the interface, **bundled locally** with no external CDN, so screens and printing keep working offline at the counter. Do not use a CDN or Google Fonts.
- A **thin serif** only for brand headings and the wordmark (propose **Cormorant Garamond** or a similar thin serif, also bundled locally). It is never used for dense UI text.
- Scale (committed in BRAND-01; the exact font files are BRAND-02):

| Group | Values |
|---|---|
| Text sizes | 12, 14, 16, 20, 24, 32, 40 px, expressed as rem |
| Line heights | 1.2 (headings), 1.5 (body) |
| Spacing | 4, 8, 12, 16, 24, 32, 48, 64 px |
| Radius | 4, 8, 12 px, pill 999 px |

- The exact font files are added in **BRAND-02** and must be checked for complete **Arabic glyphs** (all letters, diacritics where used, and correct shaping) before they are accepted.

## 4. Where it applies

- **Diva Ops:** the staff PWA uses the navy-and-gold shell in both light and dark mode.
- **Control Room:** the management dashboard shares the same shell and tokens.
- **Mini App:** the Telegram Mini App uses the same tokens, tuned for small screens.
- **POS Next:** themed through small, tracked CSS-variable overrides in `infra/posnext-patches`; never an untracked edit, and rebased on every upgrade.
- **Receipts:** 80 mm thermal receipts follow the palette and font at small sizes.
- **Labels:** product labels use the same tokens and the bundled Arabic font.
- **Invoices and print headers:** A4 documents carry the brand header.
- **Telegram channel avatar:** the logo version used for the channel avatar.
- **Publishing templates:** post templates for social and messaging channels.

**ERPNext Desk stays stock.** Only the logo and the app name are set, through Navbar and Website settings, via `infra/erpnext-config` — configuration data only, task **BRAND-05**. There is **no Desk theme app in production**: installing one would be a third exception to the no-custom-code rule in `AGENTS.md`, and the project allows only the two governed exceptions (POS Next and `diva_guard`). A Desk theme trial, if the owner wants one, is **dev-only, optional, and must not ship**.

## 5. Rules

- All colors come from tokens, **never hard-coded**.
- Tokens exist as `packages/ui/tokens.css` (CSS variables, light and dark) and `packages/ui/tokens.json`.
- RTL and LTR are both supported; layout and styling must not assume one direction.
- Every text pair must pass **WCAG AA** (4.5:1 for normal text).
- Gold is never used for text on light backgrounds.
- Borders are decorative and exempt from the contrast rule.
- The contrast check is a **unit test** that fails the build if any text pair drops below AA.

## 6. Implementation tasks

| Task | Scope | Depends on |
|---|---|---|
| BRAND-01 | Tokens package (`packages/ui/tokens.css`, `tokens.json`) + contrast test | after P0-10 |
| BRAND-02 | Brand assets: original logo, transparent/gold/white versions, bundled font files, favicon and Telegram avatar, receipt and invoice headers (A4 + 80 mm), Arabic and English | none |
| BRAND-03 | Ops and Control Room shell (light/dark, RTL/LTR) | after E-13 |
| BRAND-04 | POS Next theming via CSS-variable overrides | after E-14 |
| BRAND-05 | ERPNext logo and app name via config (`infra/erpnext-config`) | after E-03 |

## 7. Open item

**OPEN-22:** the owner supplies the transparent SVG/PNG logo and, ideally, gold-on-navy and white versions for dark headers, and confirms the original file is committed at `assets/brand/logo-original.jpg`. Until then the original JPEG on a cream badge is used (see section 1).

## References

`19-localization-arabic-english.md` (font and RTL policy) · `AGENTS.md` (no hard-coded strings or colors; configuration-only ERPNext rule) · `docs/09-build-plan.md` (BRAND-01…BRAND-05) · `docs/10-quality-security.md` (contrast and accessibility checks) · `docs/12-decisions-open-items.md` (DEC-92, DEC-93, DEC-94, OPEN-22).
