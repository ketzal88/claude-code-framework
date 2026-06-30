---
description: One-screen client health snapshot (data freshness, alerts, cron failures)
argument-hint: <clientId>
---

Produce a one-screen health snapshot for client: `$ARGUMENTS`.

Write and execute an inline tsx script that reads:

1. **Client config**: `clients/{clientId}` — name, active, integraciones, targetCPA, objective.

2. **Data freshness per channel** (last 7 days): for each of META/GOOGLE/ECOMMERCE/EMAIL/LEADS:
   - Count of `channel_snapshots` docs matching `{clientId}__{CHANNEL}__{date}` for last 7 days
   - Last date present
   - Gap days (missing dates)

3. **Active alerts**: `client_snapshots/{clientId}` → read `alerts[]`, group by severity.

4. **Recent cron failures**: `cron_executions` where `clientId == $1 AND status == 'failed'` ORDER BY createdAt DESC LIMIT 10.

5. **Rolling metrics snapshot**: last 7d spend / conversions / revenue vs prior 7d (delta %).

Format output as markdown with emoji status indicators:
- 🟢 channel has 7/7 days fresh
- 🟡 gap of 1-2 days
- 🔴 gap >2 days or no data

Finish with **Recommendations** section — max 3 actions, prioritized by severity.

Read-only. Never mutate Firestore.

Command:
```bash
npx tsx --require ./scripts/load-env.cjs -e "<inline script>" -- <clientId>
```