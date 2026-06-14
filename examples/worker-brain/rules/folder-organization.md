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
| `scripts/backfill/` | Scripts que rellenan datos históricos |
| `scripts/sync/` | Scripts que sincronizan datos |
| `scripts/seed/` | Scripts que populan datos iniciales |
| `scripts/analyze/` | Scripts de análisis de datos |
| `scripts/debug/` | Scripts de diagnóstico y exploración |
| `scripts/audit/` | Scripts de auditoría y paridad |
| `scripts/migrate/` | Scripts de migración y limpieza |
| `scripts/ops/` | Herramientas operativas |
| `scripts/data/` | Archivos de datos estáticos |
| `scripts/` (raíz) | Solo scripts referenciados en `package.json`, `.claude/settings.json` o `.github/workflows/` |

## docs/ — Documentación

| Subcarpeta | Qué va ahí |
|---|---|
| `docs/screenshots/` | Capturas de pantalla de UI, testing, diseño |
| `docs/` (raíz) | Planes, roadmaps, auditorías, guías operativas |

## Regla general

Cuando crees un archivo nuevo, hacéte la pregunta: ¿Dónde vive esto a largo plazo?
Si la respuesta es "en ningún lado específico", eso es señal de que necesita una subcarpeta o pertenece a `docs/`.
