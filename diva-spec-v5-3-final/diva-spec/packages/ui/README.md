# Diva UI tokens

Shared design tokens for Diva Ops, Control Room, the Mini App, POS Next theming,
receipts, labels and print headers. Palette: **Diva Navy and Gold** (DEC-92).
The specification is `docs/27-brand-and-design-tokens.md`.

## Files

- `tokens.json` — the canonical palette, typography, spacing and radius values,
  plus the documented WCAG contrast ratios.
- `tokens.css` — the same tokens as CSS variables, light and dark.
- `test_tokens_contrast.py` — fails if any text pair drops below WCAG AA
  (4.5:1), if the documented ratios drift by more than 0.1, or if the CSS and
  JSON fall out of sync.

## Use

```css
@import "@diva/ui/tokens.css";

.card {
	background: var(--diva-color-panel);
	color: var(--diva-color-text);
	border: 1px solid var(--diva-color-border); /* decorative only */
}
```

Set `data-theme="dark"` on `<html>` for dark mode, or `data-theme="light"` to
pin light mode when the operating system prefers dark.

## Rules

- Never hard-code a color in an application; use the token.
- Gold `#C9A24B` is decorative on light backgrounds and is never used for text
  there (2.2:1).
- Every text pair must meet WCAG AA (4.5:1). Borders are decorative and exempt.
- Arabic and English, RTL and LTR, are both first-class.
