---
description: Fix `any` types in a target file, with typed replacements and baseline update
---

Walk through every `any` in a target file and replace with a properly typed alternative.

Usage: `/fix-any <path>` (e.g. `/fix-any src/lib/slack-service.ts`). If no path is passed, read `.any-baseline.json` and suggest the top 5 offenders; then ask the user to pick one.

Steps:
1. Run `node scripts/count-any.js --file <path> --json` to get the current count and confirm the file is in scope (src/**/*.{ts,tsx}).
2. Read the file. List every `any` occurrence with its line number, grouped by pattern (`: any`, `as any`, `any[]`, `<any>`, `Record<string, any>`).
3. For each occurrence, propose a typed replacement:
   - Catch blocks (`catch (e: any)`) → remove annotation + use `getErrorMessage(e)` from `src/lib/type-guards.ts`.
   - Firestore reads (`doc.data() as any`) → introduce/extend an interface in `src/types/firestore-docs.ts` (extend the `src/types/channel-rawdata.ts` pattern, never duplicate it).
   - External SDK responses (Slack, Meta, Google Ads, Klaviyo, Gemini, Apify, Notion) → add a Zod schema at the fetch boundary and consume `z.infer<typeof Schema>`. Colocate the schema next to the service.
   - Event payloads / React handlers → use the official event type (`React.FormEvent<HTMLFormElement>`, etc.).
   - Truly unknown inbound JSON → `unknown` + `asRecord()` / `hasProperty()` from `src/lib/type-guards.ts`.
4. Apply the edits. Prefer a small number of coherent edits over many tiny ones.
5. Run `npx tsc --noEmit` on the whole project (not just the file). STOP if there are new errors.
6. Run `node scripts/count-any.js --file <path>` and confirm the count dropped. If it didn't, the replacements were too weak — iterate.
7. Regenerate `.any-baseline.json` with `node scripts/count-any.js --baseline`.
8. Show the delta to the user (before → after) and propose a commit message like `refactor(<scope>): replace <N> any's in <path>` with footer `any: <prevTotal> → <nowTotal> (-<delta>)`.

Constraints:
- NEVER use `as unknown as T` without a `// justify: <reason>` comment.
- NEVER introduce a parallel taxonomy of types. Extend `src/types/channel-rawdata.ts` and (if needed) a new `src/types/firestore-docs.ts` that follows the same shape.
- If a Zod schema is the right fix but `zod` isn't installed yet, STOP and ask — don't silently add a dep.
- Escape hatch: if a type genuinely can't be narrowed (library typings are wrong), keep the cast but annotate: `const x = lib.fn() as unknown as Foo; // justify: @slack/web-api under-specifies blocks`.

Anti-patterns to refuse:
- Widening `any` → `unknown` without narrowing (pushes the problem up the stack).
- Renaming an interface member from `any` to `unknown` without a guard at the callsite.
- Disabling the rule with `// eslint-disable-next-line @typescript-eslint/no-explicit-any`.