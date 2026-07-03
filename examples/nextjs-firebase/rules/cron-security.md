# Cron Security Rules

Every route under `/api/cron/**` is security-sensitive. These rules are non-negotiable.

## Auth is mandatory

Every cron route MUST call `validateCronSecret()` as its FIRST action:

```ts
import { validateCronSecret } from '@/lib/cron-security';

export async function POST(req: NextRequest) {
  const auth = await validateCronSecret(req);
  if (!auth.valid) return auth.response;
  // ... rest of handler
}
```

Accepted auth forms (handled by `validateCronSecret`):
- `Authorization: Bearer <CRON_SECRET>` header (GET-friendly, for manual triggers)
- `x-cron-secret: <CRON_SECRET>` header (used by GitHub Actions POST calls)

Never accept unauthenticated POSTs, even for "internal" or "dev-only" cron routes. There's no such thing — they're all public-routable on Vercel.

## Error handling

Wrap the cron body with `withErrorReporting()`:

```ts
import { withErrorReporting } from '@/lib/error-reporter';

export const POST = withErrorReporting('cron-name', async (req) => {
  // handler
});
```

This logs structured errors to `system_events` collection and surfaces them in `/admin/system`.

Never `console.error` and swallow. Never catch and return 200.

## Idempotency

Cron routes can be retried by GitHub Actions or triggered manually from `/admin/cron`. Treat every run as potentially redundant:
- Use upserts (`.set(..., { merge: true })`) not blind creates.
- Use deterministic doc IDs (see `rules/firestore-conventions.md`).
- Record the run in `cron_executions` with start/end/status.

## Timeout awareness

Vercel cron max duration varies by plan. For long jobs:
- Use `export const maxDuration = 300;` (5 min max on Pro).
- For anything longer, queue work via `channel_backfill_queue` and process in chunks (see `process-backfill-queue` cron).
- If a run consistently times out, split the route, don't raise the limit.
