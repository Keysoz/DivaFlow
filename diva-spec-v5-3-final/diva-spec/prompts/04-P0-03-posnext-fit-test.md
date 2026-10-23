# TASK P0-03: POS Next fit test (staging)

Install **BrainWise `pos_next`** (`https://github.com/BrainWise-DEV/POSNext`) on a staging copy of ERPNext. Do NOT install the unrelated older "POSNext" by exvas.
Run the POS-CHECK list in `docs/07-modules-apps.md` and answer every "verify" and "unknown" cell in `docs/14-feature-decision-matrix.md`, including: ERPNext 16 compatibility, a full offline shift and sync, reserved-stock behavior, Dozen and Nos handling, `qty*barcode` multiplier, returns, customer card, Arabic UI and RTL, Arabic keyboard layout, Arabic receipt printing, hook points for `diva_guard`, and an uninstall rehearsal.
Output: a scored report and a go or no-go recommendation with reasons. If no-go, say what we build in Diva Ops instead. Do not modify POS Next yet.
