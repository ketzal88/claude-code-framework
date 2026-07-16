# Organización de Carpetas — Dónde va cada cosa

## Raíz del proyecto

La raíz solo debe contener archivos de configuración del framework/tooling:
`package.json`, `next.config.js`, `tsconfig.json`, `tailwind.config.ts`, `firestore.indexes.json`,
`firestore.rules`, `firebase.json`, `knip.json`, `vercel.json`, `playwright.config.ts`,
`instrumentation-client.ts`, `sentry.*.config.ts`, `README.md`, `next-env.d.ts`.

**Nunca dejar en la raíz:**
- Screenshots o imágenes sueltas → `docs/screenshots/`
- Documentos de análisis / planes / auditorías → `docs/`
- Archivos de datos de prueba (`.json` temporales) → `scripts/data/`
- Artefactos de Playwright (`auth.json`, etc.) → `.playwright-cli/`
- Archivos de diseño `.pen` → pueden quedar en raíz solo si son activos

## scripts/ — Estructura de subcarpetas

| Subcarpeta | Qué va ahí |
|---|---|
| `scripts/backfill/` | Scripts que rellenan datos históricos (`backfill-*`, `*-backfill*`, `process-backfill-*`, `meta-backfill-*`) |
| `scripts/sync/` | Scripts que sincronizan datos (`sync-*`, `resync-*`, `fill-empty-*`) |
| `scripts/seed/` | Scripts que populan datos iniciales (`seed-*`, `fill-competitors-*`) |
| `scripts/analyze/` | Scripts de análisis de datos (`analyze-*`, `hot-sale-*`, `brain-readiness-*`, `inspect-*`, `detailed-*`) |
| `scripts/debug/` | Scripts de diagnóstico y exploración (`check-*`, `debug-*`, `diagnose-*`, `explore-*`, `deep-check-*`, `_check-*`, `test-*` ad-hoc) |
| `scripts/audit/` | Scripts de auditoría y paridad (`audit-*`, `parity-*`) |
| `scripts/migrate/` | Scripts de migración y limpieza (`migrate-*`, `rebuild-*`, `cleanup-*`, `dedup-*`, `fix-*`, `update-*`, `detect-migration-*`) |
| `scripts/ops/` | Herramientas operativas (`create-*`, `list-*`, `generate-*`, `import-*`, `link-*`, `run-*`, `simulate-*`, `trigger-*`, `assign-*`, `delete-*`, `restore-*`, `reset-*`, `discover-*`) |
| `scripts/data/` | Archivos de datos estáticos (`.json`, `.html` de diagramas, fixtures) |
| `scripts/` (raíz) | Solo scripts referenciados en `package.json`, `.claude/settings.json` o `.github/workflows/` |

**Scripts que deben quedarse en `scripts/` raíz** (referenciados externamente):
- `load-env.cjs` — requerido por todos los `npx tsx --require`
- `test-pure-functions.ts`, `test-alert-engine.ts`, `test-parity-invariants.ts` — `package.json`
- `check-strict-parity-readiness.ts` — `package.json`
- `pre-push-check.sh`, `count-any.js`, `check-any-baseline.js`, `check-dead-code-baseline.js` — `package.json`
- `check-no-new-any.js`, `check-error-reporting.js`, `stop-dead-code-guard.py`, `pre-push-quality-guard.py`, `check-no-secrets.sh` — `settings.json` / CI
- `tn-homologation-diagram.mmd` — `package.json` (tn:diagram)
- `massive-backfill.ts` — documentado en CLAUDE.md con ruta específica

## Imports en scripts de subcarpetas

Los scripts en subcarpetas deben importar desde `../../src/` (no `../src/`):

```ts
// ✓ Correcto — script en scripts/backfill/ o cualquier subcarpeta
import { db } from '../../src/lib/firebase-admin';

// ✗ Roto — solo válido si el script está en scripts/ raíz
import { db } from '../src/lib/firebase-admin';
```

## docs/ — Documentación

| Subcarpeta | Qué va ahí |
|---|---|
| `docs/screenshots/` | Capturas de pantalla de UI, testing, diseño |
| `docs/` (raíz) | Planes, roadmaps, auditorías, guías operativas |

## Regla de destilación de workflows (a la 2ª vez, script)

10 sesiones de la auditoría 2026-07 re-ejecutaron a mano workflows operativos
recurrentes (imports de Notion con 429 de rate limit, resyncs multi-cliente
pedidos en prosa, exports mensuales, cableado de tools MCP) — cada repetición
re-descubre el procedimiento desde cero.

**La SEGUNDA vez que un workflow operativo se ejecuta a mano en sesión,
convertirlo en script parametrizado en `scripts/ops/` en el mismo turno**, con
args `--client=` / `--dry-run` y usando la **API directa con backoff** (nunca
fetches MCP interactivos para operaciones masivas — el 429 de Notion).

Candidatos ya identificados (TODO, crearlos cuando vuelvan a pedirse):
- `import-content-calendar.ts --client=X --notion-db=Y` — calendario Notion → aprobador
- `export-client-month.ts --client=X` — paquete mensual desde `channel_snapshots`
- `resync-yesterday-all.ts` — detecta y rellena D-1 faltante multi-cliente
- `add-mcp-tool.ts` — genera las 2 definiciones (mcp-tools.ts + mcp-server) desde un schema único
- `sync-framework.ts` — espejo `.claude/` → repo community (your-org/claude-code-framework)

## Regla general

Cuando crees un archivo nuevo, hacete la pregunta: ¿Dónde vive esto a largo plazo?
Si la respuesta es "en ningún lado específico", eso es señal de que necesita una subcarpeta o pertenece a `docs/`.
