# My Project

Next.js 14 + TypeScript + Firebase + Vercel.

## Key Patterns

### Pure Computation Engines
All business logic engines follow `static evaluate(input): Result[]` — zero DB access, zero network calls, zero time-dependence. Pass everything via input.

### Cron Security
All cron endpoints use `validateCronSecret()` as first call + `withErrorReporting()` wrapper.

### Error Handling
Use `reportError()` / `withErrorReporting()` from `src/lib/error-reporter.ts`.

## Testing

```bash
npx tsc --noEmit           # TypeScript check
npx tsx scripts/test.ts    # Unit tests
```

## Modular Rules

@.claude/rules/pure-engine-pattern.md
@.claude/rules/cron-security.md

## Slash Commands

- `/ts-check` — run TypeScript check
- `/commit-checkpoint` — safe commit: ts-check + tests + propose message
