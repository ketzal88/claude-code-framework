---
description: Preview a Slack digest without posting (dry-run)
argument-hint: <morning|weekly|monthly> [clientId]
---

Preview a Slack digest for: `$ARGUMENTS`.

Steps:
1. Parse `{digestType, clientId}`. If clientId absent, pick the first active client with `slackChannelId` configured.

2. Based on digestType, call the corresponding builder from `src/lib/digests/`:
   - `morning` → `buildMorningBriefing(clientId)`
   - `weekly` → `buildWeeklyReview(clientId)`
   - `monthly` → `buildMonthlyReport(clientId)`

3. Print the resulting Slack blocks to stdout as:
   - **Main message**: text + blocks rendered as readable markdown
   - **Thread replies** (if morning): each reply separated by `─── reply N ───`
   - **Stats**: N alerts, N action items, estimated token count if sent to AI Analyst

4. DO NOT call `SlackService.sendMorningBriefing()` or any post method. This is preview only.

Use inline tsx:
```bash
npx tsx --require ./scripts/load-env.cjs -e "<script>"
```

The builders are pure functions (see `.claude/rules/alert-engine-pattern.md` — same pattern). No network calls should happen.

If any builder mutates state, flag it as a bug — builders must be read-only.