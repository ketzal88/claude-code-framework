---
description: Diff local vs deployed firestore.indexes.json and deploy safely
---

Deploy Firestore composite indexes safely.

Auth: this command uses the `FIREBASE_TOKEN` env var from `.env.local` (generated once via `firebase login:ci`). Never run `firebase login` interactively — pass `--token "$FIREBASE_TOKEN"` instead. If the token is missing, tell the user to add it to `.env.local` and stop.

Loading the token (run before any `firebase` call):
```bash
export FIREBASE_TOKEN=$(grep '^FIREBASE_TOKEN=' .env.local | cut -d '=' -f2- | tr -d '"' | tr -d "'")
[ -z "$FIREBASE_TOKEN" ] && echo "FIREBASE_TOKEN missing in .env.local" && exit 1
```

Never echo, print, or include `$FIREBASE_TOKEN` in any output to the user.

Steps:
1. Read `firestore.indexes.json` (local).
2. Fetch currently deployed indexes:
   ```bash
   npx firebase firestore:indexes --token "$FIREBASE_TOKEN"
   ```
3. Diff local vs deployed. Categorize changes:
   - **New**: in local, not deployed
   - **Removed**: deployed, not in local (will be dropped!)
   - **Modified**: same fields, different config

4. Show the diff to the user in a table. For each change, include:
   - Collection + fields + query scope
   - Estimated build time (warn if any affected collection is large: `channel_snapshots`, `leads`, `meta_creatives`, `ecommerce_customers`)

5. If there are **Removed** indexes, STOP and require explicit confirmation — dropping an index breaks prod queries silently.

6. On confirmation, deploy:
   ```bash
   firebase deploy --only firestore:indexes --token "$FIREBASE_TOKEN"
   ```

7. Report the deployment status and link to Firebase console.

Never run `firebase deploy` without `--only firestore:indexes` — that would deploy everything including functions/rules.