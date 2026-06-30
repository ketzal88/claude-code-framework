---
description: Enforce the DESIGN.md visual contract on UI changes — deterministic ratchet + on-demand visual audit
---

Run the two-tier design-contract gate against the panel/product surface.

Usage: `/design-gate` (checks the whole product surface) or `/design-gate <path.tsx>` (focus the visual audit on one file).

The gate enforces the non-negotiables from [DESIGN.md](../../DESIGN.md). It is scoped to the `product`/panel register and EXCLUDES `brand`-register surfaces (`src/app/public/**`, `src/components/public/**`, `src/app/tools/**`, `src/app/portal/**`, `src/components/portal/**`) — those are designed per-task with `/impeccable`.

## Tier 1 — Deterministic ratchet (the blocking part)

1. Run:
   ```bash
   node scripts/check-design-baseline.js
   ```
2. Report the result:
   - **Exit 0, unchanged** → "✅ Design-contract sin cambios (N violaciones, todas en baseline)".
   - **Exit 0, dropped** → say the floor dropped and remind: run `npm run design-baseline` to lock the lower floor before committing.
   - **Exit 1, regressed** → list the offending files (the script prints `file: prev → now`). For each, open it and identify the exact violation:
     - `shadow-(sm|md|lg|xl|2xl|inner)` / `shadow-[…]` → replace with the tonal ramp (`bg-special`/`bg-second`) + a 1px `border border-argent`. Use `shadow-none` to opt out of an inherited shadow.
     - `rounded-[…]` arbitrary radius → drop it. Named `rounded-*` (incl. `rounded-full`) are inert (tailwind.config zeroes them) so they are NOT flagged; only arbitrary values render real radius. The spinner exception lives in `globals.css`.
     - `bg-clip-text` / `background-clip: text` → remove the gradient text; emphasis is weight, size, or `text-classic`.
   - Fix the regression, then re-run step 1 until green. Do NOT regenerate the baseline to make a regression "pass" — the baseline only moves DOWN.

## Tier 2 — Visual audit (advisory, on-demand)

The deterministic tier cannot see the rules that need judgment. After Tier 1 is green, audit the changed product `.tsx` (or `<path>` if given) against the semantic non-negotiables:

3. Invoke `/impeccable` (register: `product`) on the changed surface and check specifically:
   - **Accent ≤8% (The 8% Surface Rule)**: is `classic #F5C518` only on keywords / active stripe / primary button fill / one KPI — never a card or panel background? A yellow card background is a violation that NO grep can catch.
   - **No hero-metric template**: no gigantic centered number with supporting gradient.
   - **No-Tint Rule**: backgrounds are pure greys (`stellar/special/second`), never cream/sand/beige.
   - **Two-Family Rule**: Inter for content, JetBrains Mono only for controls/labels — no mono headlines, no Inter buttons.
4. Report Tier 2 findings as a list with file:line and the rule each one breaks. Tier 2 does **not** block — surface the findings and let the user decide.

## Notes

- Tier 1 also runs automatically as a Stop hook (`scripts/stop-design-guard.py`) on any turn that changed a `.tsx`. This command is the manual, fuller version (Tier 1 + the visual Tier 2).
- Baseline: `.design-baseline.json`. Regenerate ONLY when you genuinely reduced violations: `npm run design-baseline`.
- Bypass the Stop hook for a docs-only turn: `SKIP_DESIGN=1`.