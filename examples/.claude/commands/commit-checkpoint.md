---
description: Safe commit — auto-fix lint, run full CI checks, propose message
---

Perform a safe commit checkpoint. Goal: every commit is CI-ready before it lands.

## Steps

1. `git status` + `git diff --stat` — see what changed.

2. **ESLint auto-fix** — fix correctable lint errors before checking:
   ```bash
   npx eslint --fix "src/**/*.{ts,tsx}" --quiet 2>&1 | tail -20
   ```
   Note which files changed so they're included in the staged set.

3. If any engine/alert files changed:
   ```bash
   npm run test:alerts   # or your equivalent pure-function test suite
   ```
   STOP if tests fail.

4. `npx tsc --noEmit` — STOP if TypeScript errors.

5. `npm run lint` — STOP if lint errors remain after auto-fix.

6. `npm run test:unit` — STOP if unit tests fail.

7. **DB indexes parse** (if your project uses Firestore):
   ```bash
   python -c "import json; json.load(open('firestore.indexes.json')); print('OK')"
   ```
   STOP if malformed.

8. **any-type ratchet** (if `scripts/check-no-new-any.js` exists):
   ```bash
   node scripts/check-no-new-any.js
   ```
   STOP if new `any` types added. If count dropped, run `node scripts/count-any.js --baseline`.

9. **Dead-code ratchet**:
   ```bash
   npm run check:dead-code
   ```
   STOP if orphan count grew.

10. Show diff summary + propose commit message (scan `git log --oneline -10` for style).

11. Wait for user confirmation.

12. On confirmation:
    - Stage only specific files (NEVER `git add -A` — risks committing .env files)
    - Commit with HEREDOC + Co-Authored-By trailer
    - `git status` to verify

## Safety invariants

- Never `--amend` without explicit instruction
- Never `--no-verify`
- Never include `.env*`, `*credentials*`, `*secret*` files
- `SKIP_PREPUSH=1` only for docs-only pushes (`.md`, `.claude/**`, `docs/**`)
- If pre-commit hook fails, fix and create a NEW commit — never amend
