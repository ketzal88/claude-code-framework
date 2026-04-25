# Error Reporting Pattern — Never Use `console.error` in Services

## The rule

In service files (`src/lib/**`) and API routes (`src/app/api/**`), `console.error` is banned
as an ESLint `error`. It bypasses the centralized error reporter, which means errors:
- Don't get persisted to the events log
- Don't trigger alerts or Slack notifications
- Are invisible to the observability dashboard

Use `reportError()` / `withErrorReporting()` instead.

---

## Decision tree

| Context | Use |
|---|---|
| Error that should be persisted / alert team | `reportError(message, err)` |
| Entire route or cron wrapped | `withErrorReporting('name', handler)` |
| Configuration warning (env var missing, feature off) | `console.warn` |
| Bootstrap file with circular dependency (see below) | `// eslint-disable-next-line no-console` + keep as-is |

---

## Circular dependency exceptions

Some files legitimately cannot use `reportError()` because they are called during bootstrap
or are themselves part of the error reporting chain. These get an ESLint disable comment:

```ts
// eslint-disable-next-line no-console
console.error('[bootstrap] Firebase Admin init failed:', err);
```

Files that qualify:
- **The error reporter itself** — can't report its own failure (circular).
- **Database / Firebase admin init** — runs before services are ready.
- **External notification services** (e.g., Slack, PagerDuty) — can't use Slack to report Slack failures.

Everything else → `reportError()`. No exceptions.

---

## Scanning for violations

Use `/check-console` to find `console.error` calls that should be `reportError()`:

```bash
grep -rn "console\.error" src/lib/ src/app/api/ \
  --include="*.ts" --include="*.tsx" \
  | grep -v "eslint-disable" \
  | grep -v "// bootstrap\|// circular\|// fallback"
```

---

## ESLint config

In `.eslintrc.*`, the `no-console` rule should be set to `error` for service and API directories,
with `warn` and `log` allowed for dev convenience:

```json
{
  "rules": {
    "no-console": ["error", { "allow": ["warn", "info"] }]
  }
}
```

---

## The CI guard

The GitHub Actions workflow includes an advisory audit step that reports files missing
`withErrorReporting` in cron routes. It doesn't fail the build, but it surfaces them
in the CI summary so they don't stay hidden.
