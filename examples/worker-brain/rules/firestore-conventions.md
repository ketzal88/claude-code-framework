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

### `firestore.indexes.json` es la única fuente de verdad — evitar drift

El archivo local debe ser un espejo **exacto** de los índices del proyecto en la nube.
Cuando se desincronizan, `firebase deploy --only firestore:indexes` muestra:

```
The following indexes are defined in your project but are not present in your firestore indexes file:
    (coleccion) -- (campoA,ASCENDING) (campoB,DESCENDING)
Would you like to delete these indexes? (y/N)
```

Eso significa que esos índices existen en la nube pero **faltan en el archivo local** — drift.

**Reglas para que no vuelva a pasar:**

1. **Nunca crear índices directo en la consola de Firebase** ni con el link "create index"
   que aparece en los logs de Vercel. Siempre agregarlos primero a `firestore.indexes.json`
   y deployar con el comando. El archivo es la fuente de verdad, no la consola.
2. **Ante el prompt de borrado, responder SIEMPRE `N`** (no borrar). Borrar índices del cloud
   rompe en silencio las queries que dependen de ellos en producción.
3. **Después de responder `N`, reconciliar:** agregar al archivo local los índices que el deploy
   listó como faltantes, copiando `collectionGroup` y el orden EXACTO de campos
   (el orden de los campos define el índice — `(channel, clientId)` ≠ `(clientId, channel)`).
   Antes de agregar, verificar que respaldan una query real (`grep` de la colección en `src/`);
   si no respaldan ninguna, recién ahí evaluar borrarlas deliberadamente.
4. **Volver a deployar** — ahora el deploy no debe mostrar diff ni volver a preguntar.

Para ver los índices actuales del cloud y compararlos con el archivo local:
```bash
firebase firestore:indexes        # imprime el JSON de índices desplegados
```

Incidente de referencia (2026-06-12): faltaban en local `simulator_proyectos (clientId, updatedAt)`
y `parity_reports (channel, clientId, checkedAt)`. Ambos respaldaban queries reales
(`SimulatorService.listProyectos` sin filtro de estado; `/api/admin/parity-reports` con filtro `channel`).
Fix correcto: agregarlos al archivo local, no borrarlos.

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

## Antes de agregar un campo a un tipo de Firestore

Checklist:
- [ ] El campo es `optional` en el TypeScript interface
- [ ] Todos los reads tienen fallback o render condicional
- [ ] El write usa `merge: true` o solo sets el campo en la creación del doc
- [ ] La UI no asume que todos los docs existentes lo tienen

## Campo nuevo en el perfil de cliente (`Client`) — checklist de 5 consumidores OBLIGATORIO

Bug recurrente (5 sesiones en 3 semanas, auditoría 2026-07): un campo se agrega
al form pero no a todos sus consumidores, y "se guarda" pero se pierde. **Síntoma
de reconocimiento: "la PM completó el perfil y se perdieron los campos" = casi
seguro falta en `ALLOWED_FIELDS`** — el PATCH descarta EN SILENCIO todo campo
fuera del whitelist.

Al agregar/renombrar un campo de `Client`, grepear el nombre del campo y
confirmar que aparece en LOS 5 (o justificar la exclusión explícitamente):

1. **Whitelist del PATCH** — `ALLOWED_FIELDS` en
   `src/app/api/clients/[id]/route.ts` (~línea 96). El #1 olvidado y la causa
   del bug silencioso.
2. **Form de perfil admin** — `src/app/admin/clients/[slug]/page.tsx` (y
   `new/page.tsx` si aplica al alta).
3. **Onboarding del portal** — `src/app/portal/onboarding/**` (si el cliente
   self-service debe cargarlo).
4. **Settings del portal** — `src/app/portal/settings/**` (si el cliente debe
   poder editarlo después).
5. **Context-builder del AI Analyst** — `src/lib/ai-analyst/context-builder.ts`
   (si no va al contexto del chat, dejar constancia de por qué — "lo cargué y
   el chat no lo ve" ya pasó con marca & estrategia).

Cierre del cambio: round-trip real (guardar → recargar → ver el valor), no solo
"el PATCH devolvió 200". Ver memoria feedback_profile_field_persistence.