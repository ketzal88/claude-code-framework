---
description: Scaffold a new alert type end-to-end (engine, test, docs, wiring)
argument-hint: <engine: meta|google|ecommerce|email|leads|cross-channel> <ALERT_NAME> <severity: CRITICAL|WARNING|INFO>
---

Scaffold a new alert type: `$ARGUMENTS`.

Steps:
1. Parse args into `{engine, alertName, severity}`. Validate:
   - engine ∈ {meta, google, ecommerce, email, leads, cross-channel}
   - alertName is UPPER_SNAKE_CASE
   - severity ∈ {CRITICAL, WARNING, INFO}
2. Determine channel routing per `.claude/rules/alert-engine-pattern.md`:
   - CRITICAL / SCALING_OPPORTUNITY → `slack_immediate`
   - WARNING → `slack_weekly`
   - INFO → `panel_only`
3. Modify `src/lib/alert-engines/<engine>-alert-engine.ts`:
   - Add the alert type to the local type union.
   - Add a private `evaluate<AlertName>()` method that takes the same `input` shape and returns `Alert | null`.
   - Wire it into the main `evaluate()` method.
   - Leave a `// TODO: implement <AlertName> predicate` comment at the predicate site.
4. Add a unit test in `scripts/test-alert-engine.ts`:
   - Happy path: fixture that SHOULD trigger the alert.
   - Negative: fixture with same shape that should NOT trigger.
5. Add a row to the alert reference table in `CLAUDE.md` (under Meta Ads or Multi-Channel).
6. If engine is NOT Meta, also verify the alert is picked up by `AlertEngineOrchestrator.evaluateAllChannels()`.
7. Run `npx tsc --noEmit` to confirm no regressions.
8. Report:
   - Files modified
   - TODO locations the user must fill in (predicate logic + threshold values)
   - Next step: `/test-alerts` to validate.

Never implement the predicate logic yourself — that's a human judgment call about thresholds. Leave a well-commented TODO.