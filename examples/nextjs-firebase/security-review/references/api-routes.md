# API Routes — auth, input validation, webhooks, errores

Toda ruta bajo `src/app/api/**` es públicamente ruteable en Vercel. El middleware **no** las protege
(el matcher excluye `/api`). Cada handler se defiende solo.

## Contenido
- [Autenticar + autorizar](#authz)
- [Auth de crons](#cron)
- [Input validation y mass-assignment](#input)
- [Verificación de firma en webhooks](#webhooks)
- [Manejo de errores sin fuga](#errores)
- [Rate limiting / budget en endpoints de IA](#rate)

## <a id="authz"></a>Autenticar + autorizar (en ese orden)

Patrón base de una ruta sensible:
```ts
const user = await getAuthenticatedUser(req);      // autenticación
if (!user) return NextResponse.json({ error: 'No autenticado' }, { status: 401 });
const access = await requireClientAccess(user, clientId);  // autorización
if ('denied' in access) return access.denied;
```
Bug a buscar: autenticar pero **no** autorizar (sabe quién sos, no chequea si podés ver *este*
cliente). Ver [multi-tenant-authz.md](multi-tenant-authz.md).

## <a id="cron"></a>Auth de crons

Primera línea de todo handler en `src/app/api/cron/**`:
```ts
import { validateCronSecret } from '@/lib/cron-auth';   // módulo real (no '@/lib/cron-security')
const authError = validateCronSecret(req);              // síncrono, devuelve NextResponse | null
if (authError) return authError;
```
`validateCronSecret` ([cron-auth.ts](../../../src/lib/cron-auth.ts)) acepta `Authorization: Bearer
<CRON_SECRET>` o `x-cron-secret`, compara timing-safe, y devuelve 500 si `CRON_SECRET` no está seteado.
Nunca aceptar un POST sin auth "porque es interno" — no existe lo interno en Vercel.

> El import correcto es `@/lib/cron-auth` (síncrono, `NextResponse | null`). Hasta 2026-06-30 los
> docs (`cron-security.md`, `worker-cron`) decían `@/lib/cron-security` con firma `async` `.valid`/
> `.response` — ya corregido. Si reaparece esa firma en código nuevo, es copia de un doc viejo.

## <a id="input"></a>Input validation y mass-assignment

Patrón canónico (whitelist de campos) en
[clients/[id]/route.ts:96-141](../../../src/app/api/clients/[id]/route.ts#L96-L141):
```ts
const ALLOWED_FIELDS = ["name", "slug", "currency", /* ... explícito ... */];
const updates = Object.fromEntries(
  Object.entries(raw).filter(([key]) => ALLOWED_FIELDS.includes(key))
) as Partial<Client>;
```
Bug a buscar: un handler que hace `db.doc(id).set(body, { merge: true })` con el body crudo del request.
Eso es **mass-assignment** — el atacante puede setear cualquier campo (`role`, `active`, `team`,
`planStatus`, flags internos). Toda escritura desde input de usuario debe pasar por whitelist o por un
tipo concreto validado.

Relacionado: parsear el body como tipo concreto, no `as any` (`const body = await req.json() as ConcreteType`)
— alinea con el any-ratchet y evita campos no previstos.

## <a id="webhooks"></a>Verificación de firma en webhooks

Todo webhook entrante (Slack, Shopify, Meta, Tienda Nube, Telegram, GHL) **debe** verificar firma
antes de procesar el payload. Patrón correcto del repo: HMAC sha256 + comparación timing-safe.
- Slack: [slack/events/route.ts:45-51](../../../src/app/api/slack/events/route.ts#L45-L51) — `createHmac` + `timingSafeEqual`.
- Shopify OAuth callback, Meta data-deletion, Tienda Nube webhook: mismo patrón.

⚠️ Inconsistencia real (ejemplo de finding **Low**): `telegram/webhook` compara el secret con
`secret !== process.env.TELEGRAM_WEBHOOK_SECRET` ([telegram/webhook/route.ts:33](../../../src/app/api/telegram/webhook/route.ts#L33))
— comparación **no** timing-safe, contra el estándar del propio repo. Para un header secreto el
ataque de timing es mayormente teórico, pero rompe la consistencia. Fix: `timingSafeEqual`.

Bug a buscar: webhook nuevo que procesa el body sin verificar firma, o que verifica **después** de
hacer trabajo con efectos secundarios.

## <a id="errores"></a>Manejo de errores sin fuga

- Usar `reportError()` / `withErrorReporting('nombre', handler)` (`@/lib/error-reporter`). `console.error`
  está prohibido por lint en `src/lib/**` y `src/app/api/**` (salvo `error-reporter.ts`,
  `firebase-admin.ts`, `slack-service.ts`).
- No devolver al cliente el mensaje de error crudo / stack trace / detalle de la query. Loguear el
  detalle server-side, responder genérico (`{ error: 'Error interno' }`, 500).

## <a id="rate"></a>Rate limiting / budget en endpoints de IA

Todo endpoint que llama a Claude/Gemini necesita rate limit + budget cap **desde el día uno** (memoria
del proyecto: AI chat scope isolation). Referencias: `@/lib/rate-limit`, colección `ai_analyst_rate_limits`
(30 req/h por uid), `AI_ASSISTANT_DAILY_BUDGET`. Endpoints a verificar: `ai-analyst/chat`,
`team-chat/send`, `ai-assistant/chat`, `creative-brain/chat`. Un endpoint de IA nuevo sin estos
controles es High (abuso de costo / DoS de presupuesto). Detalle en [ai-surface.md](ai-surface.md).
