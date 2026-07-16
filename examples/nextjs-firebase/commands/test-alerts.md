---
description: Run the alert engine unit tests and interpret failures
argument-hint: [--engine=meta|google|ecommerce|email|leads|cross-channel] [--verbose]
---

Run the alert engine unit tests with: `$ARGUMENTS`.

Steps:
1. Execute:
   ```bash
   npx tsx --require ./scripts/load-env.cjs scripts/test-alert-engine.ts $ARGUMENTS
   ```
2. Parse the output. Tests are grouped per engine.
3. Report:
   - **Passing**: count per engine.
   - **Failing**: for each failure, the alert type, the input that triggered (or failed to trigger) it, and the expected vs. actual.
   - **Root cause hypothesis**: map each failure to a file in `src/lib/alert-engines/`.
4. If the engine is one of the 23 multi-channel alerts, cross-reference with `AlertEngineOrchestrator` to check wiring.

Do not modify engine code unless explicitly asked. This command is diagnostic only.

Reference: `CLAUDE.md` → "Alert Types Reference (39 total)" table.