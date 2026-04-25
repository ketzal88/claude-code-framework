---
description: Fix `any` types in a specific file — usage: /fix-any src/lib/my-file.ts
---

Fix TypeScript `any` annotations in the specified file, one at a time.

## Process

1. List all `any` occurrences in the file:
   ```bash
   grep -n ": any\b\|as any\b\|any\[\]\b\|(any)" src/lib/my-file.ts
   ```

2. For each occurrence, determine the correct type:

   | Pattern | Replacement |
   |---|---|
   | `request.json() as any` | `request.json() as ConcreteType` |
   | `(item: any) =>` in array callback | Type from the array's generic |
   | `Record<string, any>` for dynamic objects | `Record<string, unknown>` or concrete type |
   | External API response typed as `any` | Create an interface matching the response shape |
   | Error catch clause `(e: any)` | `(e: unknown)` + type guard |
   | `any[]` for a collection | Type the collection's element type |

3. After fixing each occurrence, run `npx tsc --noEmit` to verify no new errors.

4. When the file is clean, update the any-count baseline:
   ```bash
   node scripts/count-any.js --baseline
   ```

## Rules

- Never introduce `unknown` where the type is actually known — `unknown` is for genuinely unknown external inputs.
- Don't use `@ts-ignore` or `@ts-expect-error` as a shortcut.
- If a third-party library has no types, install `@types/library` or write a minimal `.d.ts`.
- Fix the type at the source, not just at the call site.
