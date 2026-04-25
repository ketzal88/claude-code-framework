---
description: List .ts/.tsx files over 800 lines — candidates to split
---

Find files that have grown too large and need to be split into focused modules.

```bash
find src/ -name "*.ts" -o -name "*.tsx" \
  | xargs wc -l 2>/dev/null \
  | sort -rn \
  | awk '$1 > 800' \
  | head -20
```

For each file over 800 lines, identify natural split boundaries:

**Signals that a file needs splitting:**
- Multiple section comments like `// ─── Meta ───`, `// ─── Email ───`
- The filename is generic (`service.ts`, `utils.ts`, `helpers.ts`) but covers many domains
- >3 unrelated export groups
- The file grew from one feature addition — it absorbed a second responsibility

**How to split:**
1. Identify the sub-responsibilities (each becomes a new file)
2. Create focused files with specific names: `context-meta.ts`, `context-email.ts`
3. Create a thin orchestrator that re-exports or calls the focused files
4. Verify all imports still resolve: `npx tsc --noEmit`

**The 800-line rule:**
Files over 800 lines are harder to reason about and make Claude's edits less reliable
(harder to hold full context). The threshold is a trigger to plan a split, not a hard
error — but it should never grow past 1200 lines without a plan to break it up.
