---
description: Run TypeScript check and report any errors
---

Run `npx tsc --noEmit` and report.

Steps:
1. Run:
   ```bash
   npx tsc --noEmit 2>&1
   ```
2. Report:
   - **Zero errors** → say "✅ Clean (0 errors)".
   - **Any errors** → show each with file:line and a 1-sentence diagnosis, grouped by file.
3. Do NOT fix anything unless I ask you to.

Note: the repo should be kept at zero errors. Any error surfaced is new and likely introduced in the last change — investigate commits since last clean build (`git log -- <file>`).