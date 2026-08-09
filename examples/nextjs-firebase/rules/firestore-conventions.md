# Firestore — convenciones

## Doc IDs (no inventar formatos nuevos)

- **Datos de canal**: `{clientId}__{CHANNEL}__{YYYY-MM-DD}` — CHANNEL en mayúscula (`META`,
  `GOOGLE`, `ECOMMERCE`, `EMAIL`, `LEADS`).
- **Por entidad**: `{clientId}__{entityId}` — `meta_creatives`, `creative_dna`.
- **Por customer**: `{clientId}__{platform}__{customerId}` — platform en minúscula.
- **Singleton por cliente**: `{clientId}` — `client_snapshots`, `creative_diversity_scores`.

`ECOMMERCE` y `EMAIL` unen varias plataformas: detectar siempre por `rawData.source`, nunca
inferir del clientId.

Init con `ignoreUndefinedProperties: true` → los `undefined` se descartan solos, pero **no
sirven para borrar** un campo existente (usar `FieldValue.delete()`; `null` se guarda).

Batch <500, `BulkWriter` para más. Índice compuesto **antes** de shippear un `where`+`orderBy`
nuevo: sin él la query falla en silencio. `firestore.indexes.json` es la fuente de verdad —
nunca crear índices desde la consola, y ante el prompt de borrado responder siempre `N`.

## Campo nuevo en `Client` — los 5 consumidores

Bug recurrente (5 sesiones): el campo se agrega al form pero se pierde al guardar. **Síntoma:
"completé el perfil y se perdieron los campos" = falta en `ALLOWED_FIELDS`**, que descarta en
silencio todo campo fuera del whitelist. Grepear el nombre y confirmar que aparece en los 5:

1. `ALLOWED_FIELDS` en `src/app/api/clients/[id]/route.ts` ← el olvidado siempre
2. Form admin `src/app/admin/clients/[slug]/page.tsx`
3. Onboarding del portal `src/app/portal/onboarding/**`
4. Settings del portal `src/app/portal/settings/**`
5. Context-builder del AI Analyst `src/lib/ai-analyst/context-builder.ts`

Cierre: round-trip real (guardar → recargar → ver el valor), no "el PATCH devolvió 200".

Campos nuevos siempre `optional` (`?`), reads con fallback, writes con `merge: true`.
