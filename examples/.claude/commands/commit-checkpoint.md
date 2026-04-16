---
description: Safe commit — runs ts-check + tests before allowing commit
---

Steps:
1. Run `git diff --stat` to see changes.
2. Run `npx tsc --noEmit`. STOP if errors.
3. Run `npx tsx scripts/test.ts`. STOP if failures.
4. Propose commit message (scan `git log --oneline -10` for style).
5. Wait for user confirmation.
6. Stage specific files (never `git add -A`), commit.

Safety: Never --amend, --no-verify, or include .env files.
