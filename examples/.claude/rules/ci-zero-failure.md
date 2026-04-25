# CI Zero-Failure — What breaks where and how to prevent it

The goal is `git push → CI green` as a structural invariant.
Achieve it by understanding exactly which tool catches which failure.

---

## Detection map (Next.js + TypeScript + Vercel)

| Problem | tsc | lint | unit tests | DB indexes | Vercel build | use-client check |
|---|---|---|---|---|---|---|
| TypeScript error | ✅ | — | — | — | ✅ | — |
| ESLint violation (no-console, etc.) | — | ✅ | — | — | ✗ | — |
| Pure function broken | — | — | ✅ | — | ✗ | — |
| DB indexes JSON malformed | — | — | — | ✅ | ✗ | — |
| "use client" missing with hooks | — | — | — | — | ✅ | ✅ |
| Server Component using browser API | — | — | — | — | ✅ | (partial) |
| Import path wrong | ✅ | — | — | — | ✅ | — |

✅ = detects | ✗ = does NOT detect | — = not applicable

---

## Rules by failure type

### TypeScript errors
- `tsc --noEmit` must pass before every push.
- `ignoreBuildErrors: false` in `next.config.js` — TypeScript errors fail Vercel.
- Run with `NODE_OPTIONS=--max-old-space-size=6144` to mirror CI (avoids OOM divergence).
- Trust `tsc`, not the IDE — the IDE can show false-clean states.

### ESLint violations
- `eslint.ignoreDuringBuilds: true` (recommended) — ESLint doesn't run during Vercel build.
  ESLint failures only affect CI, not Vercel. Set this to avoid surprise Vercel failures from lint.
- Run `npx eslint --fix` BEFORE `npm run lint` — fixes auto-correctable issues
  (import order, trailing whitespace, unused-var renames) so the check step is clean.
- The `no-console` rule as `error` (not `warn`) in service/API files is deliberate:
  `console.error` bypasses the centralized error reporter. See `error-reporting-pattern.md`.

### "use client" / Server-Client boundary (Vercel-only failure)
- Any `.tsx` component that uses React hooks (`useState`, `useEffect`, etc.) without
  `"use client"` at the top will fail the Vercel build if imported from a Server Component.
- ESLint and `tsc` do NOT catch this. Only `next build` surfaces it.
- **Rule:** Every component that uses hooks carries `"use client"` explicitly.
  Don't rely on "the parent has it" — be explicit at the component level.
- The `settings.json` PostToolUse hook warns on edit. The pre-push guard scans all `.tsx` files.

### DB indexes (Firestore / similar)
- If you have a `firestore.indexes.json` (or equivalent), validate it's parseable before push.
- A JSON typo from a merge conflict or manual edit will fail CI but not `tsc` or `lint`.
- Add this check to the CHECKS list in `pre-push-quality-guard.py`.

---

## The SKIP_PREPUSH=1 bypass — when it's legitimate

ONLY when every changed file would be ignored by CI anyway:
- `**.md` — documentation
- `.claude/**` — Claude Code config
- `docs/**` — docs directory
- `.gitignore`, `.gitattributes` — git config

For any `.ts`, `.tsx`, `.js`, `.json` (non-config), or source change:
**SKIP_PREPUSH=1 is not allowed.** The pre-push guard enforces this.

---

## When CI fails but the pre-push guard passed

This means the guard and CI are out of sync. Fix it immediately:

1. **New CI step added** that isn't in the guard → add it to `CHECKS` in `pre-push-quality-guard.py`
2. **Environment difference** (package version, Node version) → pin versions in CI and locally
3. **Flaky test** → add `--retry 2` to the test runner; investigate root cause
4. **File generated locally** not committed → find and commit or `.gitignore` it

The pre-push guard must be a strict superset of CI.

---

## Commit cycle (never skip a step)

```
eslint --fix  →  tsc --noEmit  →  lint  →  tests  →  DB indexes  →  commit
```

Use `/commit-checkpoint` to run this automatically.