# Optional Fields in Existing DB Documents

## The problem

When you add a new field to a Firestore (or similar DB) document type, existing documents
in production don't have that field. If the UI or service code treats it as required, you get:
- Silent `undefined` → `NaN` bugs in calculations
- Crashes when destructuring or calling methods on `undefined`
- Misleading "0" values that look like real data

## The rule

**Every new field added to an existing collection MUST be typed as optional in TypeScript.**

```ts
// ✅ Correct — optional field on existing collection
interface CustomerRecord {
  id: string;
  totalSpent: number;
  acquisitionSource?: string;  // added 2026-04 — not backfilled
}

// ❌ Wrong — treats new field as required
interface CustomerRecord {
  id: string;
  totalSpent: number;
  acquisitionSource: string;   // existing docs will have undefined at runtime
}
```

## UI rendering rules

1. **Gate the entire section** on the field's presence — don't render an empty state that looks like data:

```tsx
{record.acquisitionSource && (
  <AcquisitionCard source={record.acquisitionSource} />
)}
```

2. **Show "data from X date onward"** if the feature activates at a known point:

```tsx
{breakdown && Object.keys(breakdown).length > 0
  ? <BreakdownChart data={breakdown} />
  : <p className="text-muted-foreground text-sm">Datos disponibles desde activación del tracking</p>
}
```

3. **Never show 0 as a real value** for a field that might simply be absent.

## Service / computation rules

1. Guard every calculation that uses an optional field:

```ts
// ✅ Safe
const mer = data.revenue && data.spend > 0 ? data.revenue / data.spend : undefined;

// ❌ Unsafe — produces NaN silently when field is absent
const mer = data.revenue / data.spend;
```

2. In `upsertFromOrders` / similar write paths — when setting a field for the first time,
   **only set it on new documents**, never overwrite on existing ones:

```ts
// First-touch attribution — set once, never overwrite
if (isNewCustomer) {
  doc.acquisitionSource = inferAcquisitionSource(order);
}
// On update:
await docRef.set({ ...updates }, { merge: true });
// acquisitionSource is not in `updates`, so existing value is preserved
```

## Backfill strategy

When you ship a new optional field, decide explicitly:

| Data volume | Strategy |
|---|---|
| < 10K docs | Backfill script immediately, change to required after |
| 10K–100K docs | Backfill script with batching, keep optional until done |
| > 100K docs or multi-tenant | Never backfill; keep optional permanently; show "from date X" in UI |

Document the decision in a comment in the type definition:

```ts
acquisitionSource?: string; // set on creation only (first-touch). Not backfilled for pre-2026-04 customers.
```

## Checklist before shipping

- [ ] Field typed as `?` in TypeScript interface
- [ ] All UI renders gated (`field &&` or `field !== undefined`)
- [ ] All calculations guard against `undefined` (no silent NaN)
- [ ] Write path uses `merge: true` — doesn't overwrite existing value if not present in update
- [ ] Backfill decision documented in code comment
