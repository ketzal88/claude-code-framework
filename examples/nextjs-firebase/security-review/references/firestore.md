# Firestore — exposición de datos, tokens, reglas

El servidor usa el **Admin SDK**, que **bypasea `firestore.rules`**. Por eso la frontera de autorización
real para los datos no son las reglas — son los handlers de `/api/**`. Las reglas solo protegen lo que
el cliente lee con el SDK web.

## Contenido
- [ignoreUndefinedProperties y mass-assignment](#undefined)
- [Tokens OAuth y secretos en reposo](#tokens)
- [firestore.rules: qué protege de verdad](#rules)
- [Doc-ID injection](#docid)
- [PII en logs](#pii)

## <a id="undefined"></a>ignoreUndefinedProperties + merge = mass-assignment

Firestore se inicializa con `ignoreUndefinedProperties: true`. Implicancias de seguridad:
- Un `set(body, { merge: true })` con body crudo escribe **toda** clave presente. Combinar con whitelist
  (ver [api-routes.md](api-routes.md) §input). Esta es la vía más común de mass-assignment en este repo.
- No se puede borrar un campo con `undefined`/`null` — usar `FieldValue.delete()`. Un `null` queda
  guardado y puede confundir checks posteriores (`if (doc.token)` pasa con `null`? no, pero `''` sí).

## <a id="tokens"></a>Tokens OAuth y secretos en reposo

ExampleApp guarda credenciales de terceros en Firestore. Al revisar un cambio que las toca:
- Colecciones con tokens: `tiendanube_auth_tokens`, tokens Shopify/Meta/Google en docs `clients`,
  `team_2fa_tokens` (secretos TOTP **encriptados** con `TOTP_ENCRYPTION_KEY`, AES).
- Verificar: (1) el token nunca se devuelve al cliente en una respuesta JSON; (2) no se loguea; (3) el
  endpoint que lo lee está detrás de un guard admin; (4) si es un secreto 2FA/contraseña, va encriptado,
  no en claro (seguir el patrón de `team_2fa_tokens`).
- Un endpoint que devuelve el doc `clients` completo al frontend puede estar filtrando
  `metaAccessToken`/tokens — verificar que se proyectan/omiten los campos sensibles.

## <a id="rules"></a>firestore.rules: qué protege de verdad

`firestore.rules` aplica **solo** a accesos desde el SDK cliente (browser). Si una colección sensible
puede leerse client-side, las reglas deben denegarlo explícitamente. Bug a buscar: una colección nueva
con datos sensibles y reglas permisivas (`allow read: if true` o sin regla → default deny, pero
verificar que no haya un `match` padre que la abra). Deploy: `firebase deploy --only firestore:rules`.

## <a id="docid"></a>Doc-ID injection

Los doc IDs se construyen con input de usuario: `{clientId}__{CHANNEL}__{YYYY-MM-DD}`,
`{clientId}__{adId}`, etc. Riesgos:
- Un `clientId` no validado deja leer/escribir el namespace de otro cliente (vuelve a IDOR — validar
  acceso al `clientId` **antes** de construir el ID).
- Caracteres en el input que rompan el patrón (`__`, `/`) pueden colisionar IDs o crear paths
  inesperados. Validar formato del `clientId`/`adId` si viene de input libre.

## <a id="pii"></a>PII en logs y system_events

`system_events` y los logs de Vercel no deben contener: tokens, secretos, emails de clientes a escala,
ni PII de customers (`ecommerce_customers`, `leads`). Al revisar un `EventService.log()` /
`reportError()` nuevo, mirar el `metadata` — que no arrastre el token o el payload completo del request.
