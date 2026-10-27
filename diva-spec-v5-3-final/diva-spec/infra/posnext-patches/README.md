# POS Next patch set

Patches we apply on top of the vendor app **POS Next by BrainWise** (`pos_next`, repository `BrainWise-DEV/POSNext`). The app is a **governed exception** (DEC-29); this patch set is tracked in git and must stay small and rebasable (DEC-35).

## Base

- Upstream tag **`v2.0.0`** = commit `e0a52c5` (2026-09-08). The tag ships app version `1.17.0` — a vendor tag/version mismatch.
- Every upgrade: rebase these patches on the new tag, run the verification list below on staging, and rehearse uninstall (DEC-35). Never auto-upgrade.

## Patches (apply in order)

| # | Patch | Why |
|---|---|---|
| 1 | `fix(api): import cint for get_receivable_accounts` | The endpoint raised `NameError: cint`; the customer/credit UI called it and failed |
| 2 | `fix(uom): dedupe the stock UOM option and make the quantity input visible` | The UOM dialog listed "Nos" twice; the quantity field was borderless and easy to miss |
| 3 | `feat(scan): support qty*barcode multiplier` | Required patch (DEC-36/E-14b): `5*890…` adds five units in one scan |
| 4 | `fix(offline): register a root-scope service worker for /pos` | The worker was scoped under `/assets/...` and could not control `/pos` |
| 5 | `i18n(ar): translate the scan placeholder and Shift History` | Two Arabic keys were missing (native review completed 2026-10-27) |
| 6 | `fix(offline): serve the precached shell for /pos navigations` | `navigateFallback` was `null`; the shell was never served offline |
| 7 | `fix(offline): claim clients and activate the new worker immediately` | `clientsClaim` / `skipWaiting` so the first session is controlled |
| 8 | `fix(offline): absolute precache URLs for the root-served worker` | At `/pos-sw.js` the relative precache URLs resolved to `/assets/...` (404) |
| 9 | `fix(offline): absolutize the workbox import and precache injected assets` | The root worker imported `./workbox-…` (→ `/workbox-…js`, 404), aborting the install; also stops the injected registrar and prefetches the manifest |
| 10 | `fix(offline): absolute URL for the injected webmanifest precache entry` | The plugin injects that entry outside the transform; a relative URL aborts the install |
| 11 | `feat(pos): owner key map and combined scan info card` | F1–F10 and Ctrl shortcuts with `preventDefault`; a scan card shows name, code, price per Dozen, stock and the quantity added |
| 12 | `fix(keys): allow Ctrl+Z undo while the scan field has focus` | After a scan the focus sits in the search field; Ctrl+Z must still undo the last line |

## Apply

```bash
bash infra/posnext-patches/apply.sh /home/frappe/frappe-bench/apps/pos_next
```

The script refuses to apply unless the checkout is at the recorded base tag/commit, and it supplies a commit identity when the checkout has none (it works on linked worktrees too).

Then rebuild the frontend and re-deploy the assets (see `docs/appendix-posnext-fit-test.md` §1 for the dev steps and §1e for the verification results):

```bash
cd apps/pos_next/POS
export PATH=/path/to/node24/bin:$PATH
yarn install
yarn build          # writes public/pos/ and www/pos-sw.js (workbox import absolutized)
```

The production packaging (Node build stage in the image, asset deployment) belongs to TASK-E-14.

## Verify after applying or rebasing

1. `GET /api/method/pos_next.api.pos_profile.get_receivable_accounts?pos_profile=<profile>` returns 200 (no `cint` NameError).
2. Scanning a barcode opens the UOM dialog with **one** `Nos` option; scanning `3*<barcode>` pre-fills quantity 3.
3. The quantity field has a visible border/background.
4. Arabic: the item-search placeholder and "Shift History" are translated; layout mirrors (`dir=rtl`).
5. Service worker (cache-proof protocol): after one load, `navigator.serviceWorker.controller` is **non-null**; the precache cache is named after the `/pos` scope; every precache URL is absolute and 200. With the server **stopped**, opening an **unvisited** `/pos/<random>` path and reloading both serve the app shell.
6. Key map: F1 lists the shortcuts; F2 focuses the customer search; F3/F4/F5 open the last-line editor; F6 removes the last line; F7 drafts; F8 payment (asks for a customer if none); F9 prints the last invoice or warns before one exists; F10 clears (with confirmation); Ctrl+F search; Ctrl+Delete clear; Ctrl+Z undo last scan; Ctrl+R return.
7. Every scan shows the scan card (name, code, price per Dozen, stock, quantity added) and focus returns to the barcode field.
8. `make secret-scan` stays clean (no secrets in the patches).

## Rebase recipe

```bash
cd apps/pos_next
git fetch --tags
git checkout -b diva-patches <new-tag>
git am --3way /path/to/patches/v<new>/*.patch     # resolve conflicts by hand
yarn --cwd POS install && yarn --cwd POS build
# run the verification list, then update the base tag here and in the appendix
```

After deploying a new worker, clear the Frappe website cache — a stale `/pos-sw.js` otherwise persists. Serve `/pos-sw.js` with `Cache-Control: no-cache` in production (E-14 packaging).

The built worker may list `manifest.webmanifest` twice (the globbed entry and the plugin-injected one); both have the same revision, so Workbox deduplicates them. If a future build gives them different revisions, `precacheAndRoute` throws — strip one entry in `copy-sw.cjs` if that happens.

Keep the patches vendor-neutral where possible and offer them upstream (AGPL: the modified source stays available to its users).
