---
description: Scaffold a new channel integration (service, cron, OAuth, types)
argument-hint: <CHANNEL_NAME> <vendor: e.g. hubspot, pipedrive>
---

Scaffold a new channel integration: `$ARGUMENTS`.

Before starting: read `.claude/rules/firestore-conventions.md` and `.claude/rules/cron-security.md`.

Steps:
1. Parse args into `{channelName, vendor}`. `channelName` uppercase (used in doc IDs).

2. **Service file** `src/lib/<vendor>-service.ts`:
   - `fetchData(clientId, startDate, endDate)` — upstream API call
   - `aggregateByDay(data): ChannelDailySnapshot[]`
   - `syncToChannelSnapshots(clientId, startDate, endDate)` — writes to `channel_snapshots` with doc ID `{clientId}__{CHANNEL_NAME}__{YYYY-MM-DD}`
   - Detect source via `rawData.source = '<vendor>'`
   - Leave `// TODO: map vendor response to ChannelMetrics` comments

3. **OAuth route** (if applicable) `src/app/api/integrations/<vendor>/auth/route.ts` + `callback/route.ts`:
   - Use `validateCronSecret()` pattern for webhook equivalents
   - Store tokens in `clients` doc under `integraciones.<vendor>`

4. **Cron route** `src/app/api/cron/sync-<vendor>/route.ts`:
   - `validateCronSecret()` as first call
   - `withErrorReporting('sync-<vendor>', ...)` wrap
   - Iterate active clients, call service, log to `cron_executions`

5. **Types** `src/types/channel-snapshots.ts`:
   - Add `'<CHANNEL_NAME>'` to `ChannelType` union
   - Add vendor-specific fields to `ChannelMetrics` if needed (gated by source)

6. **Docs**:
   - Add row to `CLAUDE.md` → Firestore Collections + Cron Schedule
   - Add cron to `.github/workflows/*.yml` if GitHub Actions is used

7. **Alert engine** (optional scaffold):
   - Create `src/lib/alert-engines/<channel>-alert-engine.ts` with empty `evaluate()`
   - Wire in `AlertEngineOrchestrator`

8. Run `/ts-check`.

9. Report files created, TODOs to fill, and env vars needed.

Never hardcode API secrets. All creds go through `.env.local` or `clients.<clientId>.integraciones.<vendor>`.