---
description: Scan for console.error in lib/api that should use the error reporting system
---

Scan for `console.error` calls in service and API files that bypass the
centralized error reporting system.

```bash
grep -rn "console\.error" src/lib/ src/app/api/ \
  --include="*.ts" --include="*.tsx" \
  | grep -v "eslint-disable" \
  | grep -v "// bootstrap\|// circular\|// fallback"
```

For each result, determine the correct replacement:

| Context | Replace with |
|---|---|
| Error that should be persisted / alert team | `reportError(message, err)` or `withErrorReporting()` |
| Configuration warning (env var missing, feature off) | `console.warn` |
| Bootstrap file that can't use `reportError` (circular dep) | `// eslint-disable-next-line no-console` + keep as is |

Bootstrap files with legitimate `console.error` (add `eslint-disable-next-line`):
- The error reporter itself (circular: can't report its own failure)
- Database/Firebase admin init (runs before services are ready)
- External notification service (e.g., Slack — can't use Slack to report Slack failures)

Everything else → `reportError()`.
