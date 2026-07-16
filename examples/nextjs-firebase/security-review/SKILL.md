---
name: security-review
description: >
  Revisión de seguridad de cambios de código en ExampleApp — authz multi-tenant,
  auth e input-validation en rutas API, exposición de datos en Firestore, la superficie
  AI/MCP, y secrets/dependencias. Usar al revisar código por problemas de seguridad,
  ANTES de shippear cambios a auth/authz, rutas API, endpoints cron, webhooks, writes a
  Firestore, manejo de tokens OAuth, o el AI Analyst/MCP; o cuando se pide una "security
  review" / "auditoría de seguridad" / "revisá la seguridad de esto".
---

# Security Review — ExampleApp

Revisión de seguridad **anclada a este stack** (Next.js 14 App Router + Firestore Admin SDK +
multi-tenant + IA). No es un checklist genérico: ExampleApp ya tiene varios controles (hooks de
secrets, `validateCronSecret`, `requireClientAccess`). El valor está en verificar lo que es único
de acá y no re-flaggear lo que ya está cubierto.

## Cómo correr una review

1. **Scope.** Determinar el diff a revisar: `git diff main...HEAD --stat`, o los archivos que el
   usuario nombró. Una review se hace sobre un *cambio*, no sobre todo el repo (salvo que se pida).
2. **Triage automático (primer pase).** Correr el script de triage para los chequeos determinísticos:
   ```bash
   bash .claude/skills/security-review/scripts/triage.sh
   ```
   Cada hit es un **candidato**, no una verdad — hay que leer el código de cada uno. El script no
   reemplaza la revisión manual; arranca con lo barato y de alta señal.
3. **Lectura por categoría.** Para cada archivo tocado, identificar qué categorías aplican y leer la
   referencia correspondiente (tabla abajo) ANTES de juzgar. Las referencias tienen el patrón correcto
   de este repo y los gotchas reales.
4. **Reporte.** Un finding por issue, severidad + SLA, en el formato de abajo. Ordenar por severidad.
5. **Cierre honesto.** Si no se encontró nada, decirlo. No inventar findings para llenar.

## Routing — qué referencia leer según lo que tocó el cambio

| Si el cambio toca… | Leer |
|---|---|
| Acceso a datos de un cliente, roles, `clientId`, portal, login, sesiones | [references/multi-tenant-authz.md](references/multi-tenant-authz.md) |
| Una ruta `src/app/api/**` (handler POST/PATCH/GET), cron, webhook, parseo de body | [references/api-routes.md](references/api-routes.md) |
| Writes/reads a Firestore, tokens OAuth, `firestore.rules`, campos nuevos en docs | [references/firestore.md](references/firestore.md) |
| AI Analyst, MCP, prompts a Claude/Gemini, datos scrapeados/leads/transcripciones, fetch de URLs | [references/ai-surface.md](references/ai-surface.md) |
| Env vars, claves, `NEXT_PUBLIC_*`, dependencias nuevas | [references/secrets-deps.md](references/secrets-deps.md) |

## Severidad → SLA de acción

Robado (y adaptado) del skill de Bitso — convierte un hallazgo en una decisión operativa:

| Severidad | Qué significa | Acción |
|---|---|---|
| **Critical** | Explotable ya / fuga de datos entre clientes / secret expuesto | **Fix antes de mergear** |
| **High** | Riesgo real, requiere condiciones específicas | Fix en el mismo cambio o el siguiente |
| **Medium** | Hardening con impacto acotado | Fix pronto, no bloquea |
| **Low** | Consistencia / defensa en profundidad | Fix cuando convenga |

## Formato de finding

Un finding por issue, severidad primero, ubicación clickeable `file:line`:

```markdown
### [Critical] IDOR: ruta acepta clientId sin requireClientAccess

- **Ubicación**: [src/app/api/foo/route.ts:24](src/app/api/foo/route.ts#L24)
- **Qué pasa**: El handler lee `clientId` del body y consulta `channel_snapshots`
  sin validar que el usuario tenga acceso a ese cliente. Un member puede pedir datos
  de cualquier cliente cambiando el `clientId`.
- **Fix**: `const access = await requireClientAccess(user, clientId); if ('denied' in access) return access.denied;`
- **SLA**: antes de mergear
```

## Controles que YA existen — NO re-flaggear

Calibración: estos ya están resueltos. Mencionar solo si el cambio los rompe o evade.

- **Secrets en commits** → hook `PreToolUse` corre `scripts/check-no-secrets.sh` (bloquea el commit).
  Gaps reales en [references/secrets-deps.md](references/secrets-deps.md).
- **Auth de crons** → `validateCronSecret` (timing-safe), en `@/lib/cron-auth`. Síncrono, devuelve
  `NextResponse | null` (uso: `const e = validateCronSecret(req); if (e) return e;`).
- **Error reporting** → `reportError()` / `withErrorReporting()`; `console.error` está prohibido por lint
  en `src/lib/**` y `src/app/api/**` (salvo 3 archivos de infra).
- **Verificación de webhooks** → HMAC sha256 + `timingSafeEqual` en slack/shopify/meta/tiendanube.

## Qué NO es esto

- No es un linter de estilo ni el ratchet de `any`/diseño (esos corren solos en el Stop hook).
- No reemplaza un pentest. Es revisión de código a nivel de cambio, orientada a este stack.
- No corre en CI automáticamente — es on-demand, cuando se pide o antes de un cambio sensible.
