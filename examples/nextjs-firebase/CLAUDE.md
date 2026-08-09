# ExampleApp

Next.js 15 (App Router) + React 19 + TypeScript + Firestore + Vercel. Analiza Meta Ads y
datos de marketing multicanal con AI. Todo el texto user-facing va **en español**.

**Next 15:** `params` y `searchParams` son `Promise` (usar `await`); `fetch` no cachea por
default. No escribir estilo Next 14.

## Cómo trabajar con el operador

- No es developer: implementá vos. Las decisiones se ofrecen como A/B/C en criollo, nunca
  como fragmentos de código para que complete.
- **El `git push` es siempre suyo.** Commiteá al terminar trabajo sustancial; nunca pushees.
- Cerrá cada turno con: qué hice / qué decidís vos / qué queda pendiente / `Estado git: …`.

## Entorno

Windows + PowerShell. Hay una vía que funciona y una vía default que falla para casi todo
(lint, Firestore, JSON, commits multilínea) → **@.claude/rules/windows-environment.md**.
Firestore siempre por `npx tsx --require ./scripts/load-env.cjs scripts/…` (service account,
nunca vence). `firebase login` muere headless.

## Hechos del dominio que no se deducen

**Objetivo del CLIENTE ≠ objetivo de la CAMPAÑA** (causa raíz del incidente 2026-07). A nivel
cuenta —KPI, página de canal, digest, reporte, `channel_snapshots.metrics.conversions`— manda
`getClientObjective(client)`. Cada campaña se juzga con `resolveObjective()`, porque un cliente
puede mezclar objetivos legítimamente. **Nunca usar `resolveObjective` para reportar a nivel
cuenta.** El objetivo de Meta no es autoritativo: bajo ODAX `OUTCOME_*` es ambiguo y no debe
pisar señales más fuertes (`destination_type`/`optimization_goal` del adset → objetivo Meta no
ambiguo → evidencia de conversión → patrón de nombre → default del cliente).
`src/lib/objective-utils.ts` es la fuente única; nunca hardcodear nombres de métrica.

**Moneda ARS.** ROAS 50–500x, CPA $1.000–$50.000 y gasto diario en millones son **normales**,
no bugs. Ningún threshold absoluto en USD; si no hay `currency`, asumir ARS.

**Doc IDs de Firestore** (no inventar formatos nuevos) y el checklist de campo nuevo en
`Client` → **@.claude/rules/firestore-conventions.md**.

## Contratos de código

- **Alert engines**: `evaluate(input): Alert[]` puro — cero DB, cero red, cero `new Date()`.
  Alert nuevo = engine + test en el mismo cambio (`npm run test:alerts`).
- **Crons**: `validateCronSecret()` primero + `withErrorReporting()` + idempotente (upsert con
  doc ID determinístico). Tocar un cron obliga a sincronizar `vercel.json`, `crons.yml` y la
  tabla de la skill `worker-cron`, o CI se pone rojo.
- **`console.error` es error de lint** en `src/lib/**` y `src/app/api/**`: usar `reportError()`
  si debe verse en `/admin/system`, `console.warn` si es solo para el dev.
- **Toda página del panel tiene que llegar a `<AppLayout>`** (directo o vía su componente en
  `src/components/pages/`). Si falta, la página no rompe: renderiza sin sidebar ni padding.
- **Diseño** (DESIGN.md): accent `#F5C518` ≤8% de la pantalla, zero border-radius, sin
  `box-shadow` (profundidad = rampa tonal + borde 1px). UI → @.claude/rules/ui-delivery-checklist.md

## Los gates te avisan solos

Hooks y CI corren tsc, lint, tests, dead-code, contrato de diseño, page-shell, cron-doc,
secretos y `use client`. **Bloquean el turno y traen el fix en el mensaje**, así que no hace
falta memorizarlos: si algo se rompe, te enterás con la corrección exacta al lado.
`npx tsc --noEmit` y `npm run test:alerts` para verificar a mano.

## Dónde está el resto

Invocar la skill cuando haga falta el dato exacto: `nextjs-firebase-reference` (env vars, ~45
colecciones, rutas), `worker-cron` (42 crons), `worker-alerts-reference` (59 alertas),
`worker-incident-triage` (**cuando el operador pegue un error crudo, mirar acá antes de
diagnosticar**), `worker-firestore`, `worker-slack-formatting`, `security-review`,
`google-ads-ops`. Hooks documentados en [docs/claude-hooks.md](../docs/claude-hooks.md).

@.claude/rules/windows-environment.md
@.claude/rules/firestore-conventions.md
@.claude/rules/ui-delivery-checklist.md
