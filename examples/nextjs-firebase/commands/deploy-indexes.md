---
description: Diff local vs deployed firestore.indexes.json and deploy safely (headless, service account)
---

Deploy de índices compuestos de Firestore, de forma segura y **headless**.

## Cuándo lo uso (yo, Claude — el usuario NO invoca este comando)

Lo corro **automáticamente** cuando, en cualquier tarea, **agrego o modifico un índice
compuesto en `firestore.indexes.json`** — típicamente al escribir una query nueva con
`where` + `orderBy` (o un rango `>=/<=`) que necesita índice. La regla
[firestore-conventions](../rules/firestore-conventions.md) manda: **índice compuesto ANTES
de shippear la query**, si no falla en silencio en prod. No espero que el usuario lo pida:
es parte del cierre de cualquier cambio que toque Firestore.

## Auth (service account — sin token)

Usa las credenciales del service account ya presentes en `.env.local`
(`FIREBASE_PROJECT_ID` / `FIREBASE_CLIENT_EMAIL` / `FIREBASE_PRIVATE_KEY`), que tiene el rol
**Cloud Datastore Index Admin**. **No** usa `FIREBASE_TOKEN` (deprecado, se vencía seguido)
ni `firebase login`. Nunca imprimas la `FIREBASE_PRIVATE_KEY`.

## Pasos

1. **Dry-run** (diff local vs cloud, sin escribir nada):
   ```bash
   npx tsx --require ./scripts/load-env.cjs scripts/ops/deploy-firestore-indexes.ts
   ```
   Reporta:
   - **NEW**: en el archivo, falta crear en cloud → se crearían con `--apply`.
   - **DRIFT**: en cloud, falta en el archivo.

2. **Mostrar el diff** al usuario en una tabla (colección + campos + scope). Avisar de build
   largo si toca una colección grande: `channel_snapshots`, `leads`, `meta_creatives`,
   `ecommerce_customers`.

3. **Si hay DRIFT** (índices en cloud que no están en el archivo): **PARAR.** No se borra
   nunca del cloud — rompe queries de prod en silencio. Reconciliar **agregando** esos
   índices a `firestore.indexes.json` (copiando `collectionGroup` + orden EXACTO de campos)
   y volver al paso 1. El script jamás borra: solo crea.

4. **Si hay NEW** (y el DRIFT está reconciliado): aplicar.
   ```bash
   npx tsx --require ./scripts/load-env.cjs scripts/ops/deploy-firestore-indexes.ts --apply
   ```

5. **Reportar**: los índices nuevos quedan en estado `CREATING` unos minutos antes de pasar a
   `READY`. Para colecciones chicas es casi instantáneo.

## Notas

- El script (`scripts/ops/deploy-firestore-indexes.ts`) crea vía Firestore Admin REST API.
  Solo necesita `datastore.indexes.create` (que el SA tiene), a diferencia de
  `firebase deploy` que además exige `firebase.projects.get`.
- Si el dry-run da `NEW: 0 · DRIFT: 0`, local y cloud están en sync — no hay nada que hacer.
- Si en algún momento se vuelve a usar `firebase deploy --only firestore:indexes` y ofrece
  **borrar** índices (`Would you like to delete these indexes? y/N`), responder **N** y
  reconciliar agregando al archivo. Nunca borrar.
