# Code Quality Ratchets — Three Floors That Never Go Down

The project enforces three progressive ratchets. Each one has a baseline file and a check
script. The baseline is the floor — it can only go down (when you clean up), never up.

---

## 1. TypeScript `any` Ratchet

**Baseline file:** `.any-baseline.json` (per-file counts)

**Check command:**
```bash
node scripts/count-any.js
```
Exits 1 if the count in any file exceeds the baseline. Run after every file edit.

**How to fix `any` in a file:**
Use `/fix-any src/path/to/file.ts` — it scans, determines correct types, and verifies with tsc.

**Order of attack (highest value first):**
1. Library wrapper files — replace `any` with proper SDK types
2. API response shapes — create interfaces matching the actual response
3. Array callbacks — type from the array's generic parameter
4. Error catch clauses — `(e: any)` → `(e: unknown)` + type guard
5. `Record<string, any>` — → `Record<string, unknown>` or concrete type

**Rules:**
- Never introduce `unknown` where the type is actually known.
- Don't use `@ts-ignore` or `@ts-expect-error` as a shortcut.
- Fix the type at the source, not just at the call site.

**Lower the baseline** only after you genuinely cleaned up:
```bash
npm run any-baseline   # regenerate baseline
```

---

## 2. Dead Code Ratchet

**Tool:** [knip](https://knip.dev) — detects orphaned exports, files, types, unused deps.
**Config:** `knip.json`
**Baseline file:** `.dead-code-baseline.json`

**Check command:**
```bash
npm run check:dead-code
```
Exits 1 if orphan count grew vs baseline (total or per-file). Runs automatically as a Stop hook.

**When the hook blocks your turn:**
- (a) Delete the orphaned export/file.
- (b) Wire it to a real consumer.
- (c) If you cleaned up other files and the total is lower, run `npm run dead-code-baseline` to lower the floor.

**Bypass for CI-ignored files only:**
```bash
SKIP_DEADCODE=1
```

**Prevention:**
Before removing a symbol, grep for all consumers:
```bash
grep -r "MySymbol" src/ --include="*.ts" --include="*.tsx"
```
If no results outside the definition file → delete it. Never assume "nobody uses this."

---

## 3. File Size Ratchet

**Threshold:** 800 lines — trigger to plan a split. Never let a file grow past 1200 without a split plan.

**Check command (use `/check-file-size`):**
```bash
find src/ -name "*.ts" -o -name "*.tsx" \
  | xargs wc -l 2>/dev/null \
  | sort -rn \
  | awk '$1 > 800' \
  | head -20
```

**Signals a file needs splitting:**
- Multiple section comments (`// ─── Domain A ───`, `// ─── Domain B ───`)
- Generic name (`service.ts`, `utils.ts`, `helpers.ts`) covering many domains
- More than 3 unrelated export groups
- A second responsibility was added to an originally single-purpose file

**How to split:**
1. Identify sub-responsibilities (each becomes a new file).
2. Create focused files with specific names: `context-meta.ts`, `context-email.ts`.
3. Create a thin orchestrator that re-exports or calls the focused files.
4. Verify: `npx tsc --noEmit` — all imports must still resolve.

---

## Combined — the three ratchets together

```
any ratchet (count-any.js)      ← enforced by PostToolUse hook
dead code ratchet (knip)        ← enforced by Stop hook  
file size (manual, /check-file-size) ← triggered when adding to large files
```

The ratchets communicate the same principle: **once quality improves, it stays improved.**
