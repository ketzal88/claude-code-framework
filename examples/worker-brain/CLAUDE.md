<!--
  Curated example brain doc — derived from a real production Worker Brain (Next.js 14 + Firebase + TS)
  setup that runs the gates in this example faithfully. Business-specific detail (client lists, exact
  Slack channel IDs, person names, production URLs) has been redacted/generalized for public publishing.
  The STRUCTURE and PATTERNS below mirror the real setup — that is the point of the example.
-->

# Worker Brain — Project Brain (example)

Next.js 14 (App Router) + TypeScript app that analyzes multi-channel marketing data using AI.

**Stack:** Next.js 14, TypeScript, Tailwind CSS, Firebase (Firestore + Auth), Anthropic Claude, Gemini, Vercel.

---

## Environment Variables (.env.local)

Names only — never commit values (the `secret-scan` pre-commit gate blocks that).

```env
NEXT_PUBLIC_FIREBASE_*=...      # Firebase public config
FIREBASE_PROJECT_ID / FIREBASE_CLIENT_EMAIL / FIREBASE_PRIVATE_KEY=...
ANTHROPIC_API_KEY=...
GEMINI_API_KEY / GEMINI_MODEL=...
CRON_SECRET=...
SLACK_BOT_TOKEN / SLACK_SIGNING_SECRET=...
```

---

## Firestore Collections (representative)

| Collection | Doc ID Format | Purpose |
|---|---|---|
| `clients` | auto | Client configs, account IDs, channels |
| `channel_snapshots` | `clientId__CHANNEL__YYYY-MM-DD` | Unified daily metrics per channel |
| `client_snapshots` | `clientId` | Pre-computed snapshots with alerts |
| `system_events` | auto | Observability event log |
| `cron_executions` | auto | Cron job history |

**Firestore config:** `ignoreUndefinedProperties: true` on initialization.

---

## Key Architectural Patterns

### AlertEngine — Pure Computation
`AlertEngine.evaluate(input): Alert[]` — zero DB access. Both the cron path and the snapshot path
call `evaluate()` with already-fetched data. Unit tests work without Firebase. All engines follow
this same pattern. → `@.claude/rules/alert-engine-pattern.md`

### Objective-Aware Pipeline
A single source of truth maps objective → metric. All engines resolve via `resolveObjective()` /
`getPrimaryMetric()` — never hardcode metric checks.

### Alert Channel Routing
- `slack_immediate`: CRITICAL → morning briefing
- `slack_weekly`: WARNING → weekly review
- `panel_only`: INFO → dashboard only

### Cron Security
All cron endpoints call `validateCronSecret()` first + are wrapped with `withErrorReporting()`.
→ `@.claude/rules/cron-security.md`

### Error Handling
Use `reportError()` / `withErrorReporting()` — centralizes structured error capture.
`console.error` is forbidden in `src/lib/**` and `src/app/api/**`. → `@.claude/rules/console-error-pattern.md`

---

## Testing

```bash
npx tsc --noEmit          # 0 errors policy
npm run test:alerts       # alert engine unit tests
npm run test:unit         # pure function tests
npm run check:design      # visual-contract ratchet
npm run check:cron-doc    # cron table doc-sync
```

The blocking pre-push gate (`scripts/pre-push-quality-guard.py`) mirrors CI: tsc + lint +
test:alerts + test:unit + check:design + check:cron-doc + the opt-in `sentrux` structural ratchet.

---

## Modular Rules

@.claude/rules/operating-procedure.md
@.claude/rules/firestore-conventions.md
@.claude/rules/alert-engine-pattern.md
@.claude/rules/cron-security.md
@.claude/rules/console-error-pattern.md
@.claude/rules/regional-thresholds.md
@.claude/rules/code-quality-ratchets.md
@.claude/rules/ci-zero-failure.md
@.claude/rules/folder-organization.md
