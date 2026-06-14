---
description: Run massive backfill for a specific client and/or channel
argument-hint: [clientId] [--channel=META|GOOGLE|ECOMMERCE|EMAIL|LEADS] [--dry-run] [--reset]
---

Run the massive backfill script for the arguments provided: `$ARGUMENTS`.

Steps:
1. Parse the arguments. If a clientId was provided, prepend `--client=<id>`.
2. If `--dry-run` is present, run it first and summarize what would be written before the real run. Do NOT proceed to real run without my explicit confirmation.
3. Command to execute:
   ```bash
   npx tsx --require ./scripts/load-env.cjs scripts/massive-backfill.ts $ARGUMENTS
   ```
4. After execution, read `backfill_progress/massive_2025_2026` in Firestore (via a small inline tsx snippet) and report:
   - Tasks completed / pending / failed
   - Firestore writes consumed vs the 18K budget
   - Next recommended run (which tasks remain)

Safety rules:
- If no `--client` is provided AND no `--channel`, STOP and ask whether the user really wants to backfill everything.
- Never pass `--reset` without explicit user confirmation (it wipes progress).
- Report duration and any rate-limit warnings surfaced by the script.
