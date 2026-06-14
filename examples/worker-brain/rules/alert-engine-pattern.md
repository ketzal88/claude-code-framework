# Alert Engine Pattern

All alert engines in this codebase follow the same **pure computation** pattern.

## The contract

```ts
class SomeAlertEngine {
  static evaluate(input: AlertEvaluationInput): Alert[] {
    // zero DB access — all data is in `input`
  }
}
```

- **No Firestore reads** inside `evaluate()`.
- **No network calls** inside `evaluate()`.
- **No time-dependence** beyond what's in `input` (don't call `new Date()` — pass a reference date in).
- Returns a plain array of `Alert` objects.

Why: this makes every engine unit-testable without mocks, and lets both the cron path (`AlertEngine.run()`) and the snapshot path (`ClientSnapshotService.computeAndStore()`) share the exact same logic.

## When adding a new alert type

1. Add the alert type to the correct engine in `src/lib/alert-engines/`.
2. Add the alert to the reference table in CLAUDE.md → "Alert Types Reference".
3. Wire it in `AlertEngineOrchestrator.evaluateAllChannels()` if it's cross-channel.
4. Assign a severity + channel route:
   - `CRITICAL` or `SCALING_OPPORTUNITY` → `slack_immediate` → morning briefing
   - `WARNING` → `slack_weekly` → Monday weekly review
   - `INFO` → `panel_only` → dashboard only
5. Add a unit test in `scripts/test-alert-engine.ts` covering happy path + a negative case.

## When modifying an existing alert

- Run `/test-alerts` before and after. The snapshot count should only change for the alert you touched.
- If you change severity, update the reference table in CLAUDE.md in the same commit.

## Objective-awareness is mandatory

Never hardcode metric names like `metrics.purchases` or `metrics.leads`. Always resolve via:

```ts
import { resolveObjective, getPrimaryMetric } from '@/lib/objective-utils';
```

Supported objectives: `sales`, `leads`, `messaging`, `scheduling`, `traffic`, `awareness`, `app_installs`, `video_views`.
