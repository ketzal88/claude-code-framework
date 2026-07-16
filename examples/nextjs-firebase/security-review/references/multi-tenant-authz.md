# Multi-tenant Authorization — el riesgo #1 de ExampleApp

ExampleApp es multi-tenant: un equipo opera sobre ~45 clientes. El riesgo dominante es **acceso
cruzado entre clientes** (IDOR) y **escalación de rol**. Esta es la primera categoría a revisar en
cualquier ruta que toque datos de cliente.

## Contenido
- [Los tres sistemas de auth que coexisten](#tres-sistemas)
- [El guard de cliente y su gap actual](#client-guard)
- [IDOR: toda ruta con clientId necesita guard](#idor)
- [Aislamiento del portal](#portal)
- [El bypass de localhost](#localhost)
- [Revocación de acceso](#revocacion)

## <a id="tres-sistemas"></a>Los tres sistemas de auth (intencional)

1. **`ADMIN_UIDS`** (env CSV) → enforcement en el **middleware Edge** (`src/middleware.ts`). El Edge
   no puede leer Firestore, por eso usa una env var. Gatea `adminOnlyRoutes` (`/admin/alerts`,
   `/admin/cron`, `/admin/system`, etc.).
2. **`users.role`** (`'admin' | 'member'`) + `teamId` → lógica de negocio en las rutas API vía
   `getAuthenticatedUser()` (`@/lib/auth-helpers`).
3. **`admin_users.role = 'super'`** → propuestas y funciones SUPER (el operador, el operador).

Al revisar: el middleware protege *navegación* a páginas. **No protege las rutas `/api/**`** (el matcher
las excluye: `"/((?!api|...).*)"`). Por lo tanto **cada handler de `/api/**` debe autenticar y autorizar
por su cuenta** — no asumir que "el middleware ya lo cubre".

## <a id="client-guard"></a>El guard de cliente — y su gap actual

`requireClientAccess(user, clientId)` en `@/lib/auth-client-guard` devuelve
`{ client } | { denied: NextResponse }`. Uso correcto:

```ts
const access = await requireClientAccess(user, clientId);
if ('denied' in access) return access.denied;
const { client } = access; // ya cargado, evita un segundo fetch
```

⚠️ **Gap real (verificar intención con el usuario):** hoy el guard **no compara
`client.team === user.teamId`**. Para un member con cualquier `teamId`, devuelve `{ client }` para
*cualquier* cliente (ver [auth-client-guard.ts:34-42](../../../src/lib/auth-client-guard.ts#L34-L42)).
El comentario del código lo dice ("member con teamId: accede a todos los clientes"), pero CLAUDE.md
afirma que **sí** scopea por team. Es un equipo chico y de confianza, así que puede ser deliberado —
pero es una decisión de seguridad que debería ser explícita, no un drift silencioso entre doc y código.
Si se decide enforcar el scoping, el fix es agregar `if (client.team !== user.teamId) return { denied: 403 }`
antes del `return { client }` final.

## <a id="idor"></a>IDOR: toda ruta con clientId necesita un guard

Patrón de bug a buscar: un handler que lee `clientId` (del body, query o `params.id`) y consulta
Firestore **sin** pasar por un guard. Eso permite a un usuario pedir datos de un cliente que no le
corresponde cambiando el parámetro.

Guards válidos según la superficie:
- Rutas del panel interno → `getAuthenticatedUser()` + `requireClientAccess()`.
- Rutas admin-only → `getAuthenticatedUser()` + chequeo de rol/`ADMIN_UIDS`.
- Rutas del portal cliente → `requirePortalSession()` / `requireActivePortalClient()`.
- Crons → `validateCronSecret()`.
- MCP → `isAllowedMcpEmail()`.

El script de triage lista rutas que tocan `clientId`/`params.id` sin importar ningún guard conocido.
Falsos positivos esperables (admin routes que chequean rol inline) — leer cada una.

## <a id="portal"></a>Aislamiento del portal (clientes externos)

El portal (`/portal/**`) corre **en el mismo dominio y Firebase Auth** que el panel interno, pero es
otra superficie de confianza. Reglas:

- Sesión separada: cookie `portal-session` (no `session`), rol `'client'`, colecciones `portal_users` /
  `portal_clients` (no `users` / `clients`).
- `requirePortalSession()` (`@/lib/portal/portal-session`) **rechaza emails @example.com** con 403
  (`isWorkerEmail`) — un miembro del equipo no debe poder mirar el portal de un cliente vía su sesión.
- `requireActivePortalClient()` agrega 402 si el plan no está activo — usar en endpoints que cuestan
  plata (AI analyst, sync manual). La redirección client-side a `/portal/locked` es UX, **no**
  enforcement.
- **Leak conocido (memoria del proyecto):** el root layout monta `AuthProvider`/`ClientProvider`
  sobre `/portal`, así que los contextos internos pueden filtrarse / dar 401. Datos del portal solo
  vía `/api/portal/*` + `requirePortalSession`. No reusar servicios/contextos internos en el portal.

Al revisar un cambio del portal: verificar que no toca lógica del brain interno (rutas/servicios/crons
separados) y que todo endpoint nuevo pasa por `requirePortalSession`.

## <a id="localhost"></a>El bypass de localhost — doble gate obligatorio

Tanto `middleware.ts` como `getAuthenticatedUser()` saltean auth en dev, devolviendo un admin
sintético. El gate es **doble**: `NODE_ENV === 'development'` **Y** `host` incluye `localhost`. Si un
cambio agrega un bypass nuevo, debe replicar exactamente ese doble gate — un bypass gateado solo por
`NODE_ENV` o por un header manipulable es Critical (auth bypass en prod).

## <a id="revocacion"></a>Revocación de acceso

`active: false` en el doc `users` corta el acceso en el próximo request (`getAuthenticatedUser` devuelve
`null`). Si un cambio cachea el user o saltea ese chequeo, rompe la revocación — flaggear.
