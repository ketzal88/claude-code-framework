# My Project

Next.js 14 + TypeScript + Firebase + Vercel.

---

## Key Architectural Patterns

### Pure Computation Engines
All business logic engines follow `static evaluate(input): Result[]` — zero DB access,
zero network calls, zero time-dependence. Pass everything via `input`.
See: `@.claude/rules/pure-engine-pattern.md`

### Cron Security
All cron endpoints use `validateCronSecret()` as first call + `withErrorReporting()` wrapper.
See: `@.claude/rules/cron-security.md`

### Error Handling
Use `reportError()` / `withErrorReporting()` from `src/lib/error-reporter.ts`.
`console.error` is banned in service and API files. See: `@.claude/rules/error-reporting-pattern.md`

---

## CI Zero-Failure Philosophy

`git push → CI green` is a structural invariant, not a goal. Achieved through:

1. **Pre-push guard** (`scripts/pre-push-quality-guard.py`) runs all CI steps locally before push.
   The guard is a strict superset of CI — if CI adds a step, the guard gets it too.

2. **Commit checkpoint** (`/commit-checkpoint`) sequences all quality checks in the right order
   before any commit: `eslint --fix → tsc → lint → tests → indexes → commit`.

3. **Hooks** enforce quality at the moment of action, not after the fact.

See: `@.claude/rules/ci-zero-failure.md`

---

## Code Quality Ratchets

Three quality floors that never go down:
- **`any` ratchet** — baseline per file, PostToolUse hook enforces
- **Dead code ratchet** — knip baseline, Stop hook enforces
- **File size** — 800 line trigger, `/check-file-size` command

See: `@.claude/rules/code-quality-ratchets.md`

---

## Optional Fields on Existing Collections

Every new field on an existing Firestore collection MUST be typed as `?` in TypeScript.
Gate all UI renders and calculations. Never show `0` for a missing field.
See: `@.claude/rules/optional-fields-migration.md`

---

## Testing

```bash
npx tsc --noEmit           # TypeScript check (must be 0 errors)
npx tsx scripts/test.ts    # Unit tests
npm run lint               # ESLint (run eslint --fix first)
npm run check:dead-code    # Dead code ratchet
```

**Full pre-push check (mirrors CI exactly):**
```bash
npm run test:pre-push      # tsc + lint + tests + indexes parse
```

---

## Modular Rules

@.claude/rules/pure-engine-pattern.md
@.claude/rules/cron-security.md
@.claude/rules/ci-zero-failure.md
@.claude/rules/code-quality-ratchets.md
@.claude/rules/error-reporting-pattern.md
@.claude/rules/optional-fields-migration.md

---

## Slash Commands

### Quality & Safety
- `/commit-checkpoint` — safe commit: eslint fix → tsc → lint → tests → indexes → propose message
- `/ts-check` — run `tsc --noEmit` and report errors
- `/ci-simulate` — run all CI steps locally (all steps, all failures visible at once)

### Code Quality
- `/fix-any src/path/to/file.ts` — fix TypeScript `any` types in a specific file
- `/check-file-size` — list .ts/.tsx files over 800 lines — candidates to split
- `/check-console` — scan for `console.error` in lib/api that should use `reportError()`

---

## Hooks (auto-run via `.claude/settings.json`)

- **PreToolUse `git commit`**: runs `scripts/check-no-secrets.sh` — scans staged diff for
  credentials (PEM keys, API tokens, OAuth secrets, generic `api_key=...`). Blocks if found.
  Must be `PreToolUse` — after commit completes, `git diff --cached` is empty.

- **PreToolUse `git push`**: runs `scripts/pre-push-quality-guard.py` — mirrors CI exactly
  (tsc + lint + tests + indexes parse + use-client boundary check). Blocks on any failure.
  Bypass with `SKIP_PREPUSH=1` only when ALL changed files are docs-only (.md, .claude/**, docs/**).

- **PostToolUse Edit/Write on `.tsx`**: warns if hooks are used without `"use client"` directive.
  `tsc` and `lint` don't catch this — only `next build` surfaces it, failing the Vercel deploy.

- **PostToolUse Edit/Write on `.ts/.tsx`**: runs `any` count check — warns if count increased vs baseline.

- **Stop hook**: runs `npm run check:dead-code` (knip ratchet) before Claude ends a turn.
  Blocks if orphan count grew vs `.dead-code-baseline.json`. Bypass: `SKIP_DEADCODE=1`.