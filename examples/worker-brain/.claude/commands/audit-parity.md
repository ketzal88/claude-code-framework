---
description: Audit data parity between channel UIs and channel_snapshots collection
argument-hint: [clientId] [--channel=META|GOOGLE|ECOMMERCE|EMAIL] [--days=14]
---

Audit data parity for: `$ARGUMENTS`.

Goal: detect mismatches between what the channel UI shows (or what the upstream API returns) and what's stored in the `channel_snapshots` Firestore collection.

Steps:
1. Parse arguments. Default to `--days=14` if not provided.
2. For the target client(s) and channel(s):
   - Read `channel_snapshots` docs matching `{clientId}__{CHANNEL}__{YYYY-MM-DD}` for the date range.
   - For each day, re-fetch the upstream source (live API or service aggregate) using the existing service module (`meta-ads-service`, `google-ads-service`, etc.).
   - Compare primary metric (spend + conversions + revenue) within 1% tolerance.
3. Produce a markdown report with:
   - **Summary table**: channel × days checked × days with drift
   - **Drift details**: for each failing day, stored vs. live values + suspected cause
   - **Recommendations**: which service/cron likely caused the drift
4. If new drift is found, append findings to `DATA_PARITY_AUDIT_<YYYY_MM_DD>.md` at repo root.

References:
- Previous audit: `DATA_PARITY_AUDIT_2026_04_13.md`
- Known root causes: ecommerce timezone overwrite, Klaviyo single-snapshot, cron timeout. See memory `project_data_parity_fix_2026_04.md`.
- Service files: `src/lib/{meta-ads,google-ads,shopify,tiendanube,woocommerce,klaviyo,perfit}-service.ts`

Never mutate Firestore during this audit — read-only.