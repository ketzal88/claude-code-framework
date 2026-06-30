---
description: Validate that all env vars documented in CLAUDE.md exist in .env.local
---

Validate env vars completeness.

Steps:
1. Extract the env var block from `.claude/CLAUDE.md` (section "Environment Variables (.env.local)").
2. Read `.env.local` (if present) and list the keys defined.
3. Read `vercel.json` or suggest `vercel env ls` manually (don't execute — network + auth).
4. Produce a table:
   | Var | CLAUDE.md | .env.local | Notes |
   |---|---|---|---|
   | `GEMINI_API_KEY` | ✅ | ✅ | |
   | `APIFY_API_TOKEN` | ✅ | ❌ | Required for competitor scraping |

5. Highlight:
   - **Missing in .env.local** (would cause runtime errors)
   - **Present in .env.local but undocumented** (consider adding to CLAUDE.md or removing if unused)
   - **Sensitive vars with placeholder values** (anything matching `...|TODO|REPLACE_ME|xxx`)

6. For missing required vars, show where they're used:
   ```bash
   grep -rn "process.env.<VAR>" src/ --include=*.ts -l
   ```

Never print the actual values — only var names and presence booleans. This output may be shared.