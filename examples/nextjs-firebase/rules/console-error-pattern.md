# Console vs reportError — Cuándo usar cada uno

Esta codebase tiene ESLint `no-console` activo para `src/lib/**` y `src/app/api/**`
con `["error", { "allow": ["warn", "log"] }]`. Esto significa que `console.error` es
un error de lint en esos paths. Hay reglas distintas para cada capa.

## La regla general

```
console.error → PROHIBIDO en lib/ y app/api/
console.warn  → OK para advertencias de configuración, estado degradado
reportError() → Obligatorio para errores que deben llegar a Firestore/Slack
```

## Árbol de decisión

1. **¿Es un error en código de negocio (cron, route handler, service)?**
   → Usar `reportError(msg, err)` o `withErrorReporting()`.
   Esto escribe en `system_events` y puede disparar Slack.

2. **¿Es código de infraestructura circular que no puede usar reportError?**
   Tres archivos en esta categoría — tienen `eslint-disable-next-line no-console`:
   - `src/lib/error-reporter.ts` — el fallback de último recurso cuando EventService falla
   - `src/lib/firebase-admin.ts` — el init de Firebase no puede usar reportError (circular)
   - `src/lib/slack-service.ts` — Slack no puede reportar sus propios fallos a Slack
   → En estos archivos, `console.warn` (no `.error`) para fallos soft, y
     `// eslint-disable-next-line no-console` solo donde `console.error` sea
     genuinamente el último recurso (ej: bootstrap de Firebase que no tiene alternativa).

3. **¿Es una advertencia de configuración (ej: env var faltante, feature flag off)?**
   → `console.warn` — no es un error, es información para el desarrollador.

4. **¿Es cron-auth validando que el secret no está configurado?**
   → `console.warn` — configuración, no error de runtime.

## Regla de oro

> Si el error tiene que aparecer en `/admin/system`, usar `reportError()`.
> Si el error es solo para el dev que lee los logs de Vercel, usar `console.warn`.
> Si el archivo es uno de los tres de infraestructura circular, usar el patrón del
> archivo existente (mix de `console.warn` + `eslint-disable-next-line` donde necesario).

## Antes de editar cualquier archivo en src/lib/ o src/app/api/

Verificar si ya tiene `console.error` y reemplazarlo:
```bash
grep -n "console.error" src/lib/mi-archivo.ts
```
Si aparece, reemplazar por `console.warn` (si es advertencia de config) o
`reportError()` (si es error de runtime que debe persistir).
