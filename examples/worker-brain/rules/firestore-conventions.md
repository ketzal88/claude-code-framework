# Firestore Conventions

Rules for reading and writing Firestore in this codebase.

## Doc ID format rules
- **Channel data**: `{clientId}__{CHANNEL}__{YYYY-MM-DD}` — used by `channel_snapshots`. CHANNEL is uppercase: `META`, `GOOGLE`, `ECOMMERCE`, `EMAIL`, `LEADS`.
- **Per-entity data**: `{clientId}__{entityId}` — used by `meta_creatives`, `creative_dna`.
- **Per-customer**: `{clientId}__{platform}__{customerId}` — used by `ecommerce_customers`. `platform` is lowercase: `shopify`, `tiendanube`, `woocommerce`.
- **Per-client singleton**: `{clientId}` — used by `client_snapshots`, `creative_diversity_scores`.

Never invent new ID conventions. If you need a new collection, follow one of these four patterns.

## Initialization
Firestore is initialized with `ignoreUndefinedProperties: true`. This means:
- You **can** pass objects with `undefined` fields — they are stripped automatically.
- You **cannot** rely on this to delete existing fields. Use `FieldValue.delete()` for that.
- Never use `null` as a "please delete this" sentinel. Firestore stores nulls.

## Sub-source detection
Both `ECOMMERCE` and `EMAIL` snapshots union multiple platforms. Always detect via `rawData.source`:
- Ecommerce: `shopify`, `tiendanube`, `woocommerce`
- Email: `klaviyo`, `perfit`

Never infer source from the clientId or hardcode assumptions.

## Indexes
Composite indexes live in `firestore.indexes.json`. Deploy with:
```bash
firebase deploy --only firestore:indexes
```
When you add a `where` + `orderBy` combo that's new, add the index BEFORE shipping — queries silently fail otherwise with a link in the server console.

## Batched writes
- Use `BulkWriter` for >500 writes, `batch()` for <500.
- Always chunk by 500 max per batch (Firestore hard limit).
- Backfill budget: 18K writes/run. Track with `backfill_progress/massive_2025_2026`.

## Agregar campos opcionales a documentos existentes

Cuando se agrega un campo nuevo `opcional` a un tipo de documento Firestore:

1. **El campo NO existe en documentos ya escritos.** El código que lee ese campo
   SIEMPRE debe manejar `undefined` sin romperse:
   ```ts
   // ✓ Correcto
   const source = customer.acquisitionSource ?? "unknown";
   // ✗ Roto para docs viejos
   const source = customer.acquisitionSource.toLowerCase();
   ```

2. **En la UI, renderizar condicionalmente:**
   ```tsx
   // ✓ Solo muestra la sección cuando hay datos
   {customer.acquisitionBreakdown && <AcquisitionCard data={customer.acquisitionBreakdown} />}
   ```

3. **En writes, usar `merge: true`** — No sobreescribir el doc completo, solo setear
   el campo nuevo:
   ```ts
   await db.doc(id).set({ newField: value }, { merge: true });
   ```

4. **En el type de TypeScript, el campo debe ser `optional` (`?`):**
   ```ts
   acquisitionSource?: string;  // ← obligatorio el ? para nuevos campos
   ```

5. **No backfillear inmediatamente.** Los datos llegan organicamente en el siguiente sync.
   Solo crear un script de backfill si el campo es crítico para un feature que lo necesita.
