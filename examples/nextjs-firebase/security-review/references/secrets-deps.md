# Secrets y dependencias

## Contenido
- [El scanner pre-commit y sus gaps](#scanner)
- [NEXT_PUBLIC_ = público](#nextpublic)
- [Reglas de manejo de secretos](#reglas)
- [Dependencias](#deps)

## <a id="scanner"></a>El scanner pre-commit y sus gaps

`scripts/check-no-secrets.sh` corre como hook `PreToolUse` en `git commit` y **bloquea** el commit si
matchea. Cubre: PEM/RSA private keys, AWS (`AKIA…`), Google OAuth (`AIza…`), Anthropic/OpenAI
(`sk-ant-`/`sk-proj-`), Slack (`xox…`), Meta long-lived (`EAA…`), y asignaciones genéricas
`api_key/access_token/client_secret/refresh_token/private_key = '…'` de ≥32 chars.

Gaps reales a tener presentes (el scanner no los agarra):
- **Solo escanea el diff staged de archivos de texto.** Un secreto ya commiteado antes de que existiera
  el hook no se detecta. Para auditar histórico: `git log -p -S 'patrón'` o `git secrets`/`trufflehog`.
- **Saltea `*.md` y `.env.example`.** Un secreto real pegado en un `.md` (o en un ejemplo que dejó de
  ser ejemplo) pasa.
- **Solo nombres de variable conocidos.** Un secreto en una var con nombre raro (`const x = 'sk-…'`) cae
  en los patrones por-proveedor, pero un token propietario sin prefijo reconocible no.
- Bypass: `--no-verify` requiere aprobación explícita del usuario (CLAUDE.md).

Al revisar: si un cambio agrega una credencial de un proveedor **nuevo** (un formato que el scanner no
conoce), proponer sumar el patrón al array `PATTERNS` del scanner en el mismo cambio.

## <a id="nextpublic"></a>NEXT_PUBLIC_ = público (chequeo de alto valor)

Cualquier env var con prefijo `NEXT_PUBLIC_` se **inlinea en el bundle de JavaScript del browser**.
Un secreto ahí es público — cualquiera lo lee en las DevTools. Bug a buscar: un secreto server-side
expuesto vía `NEXT_PUBLIC_*`, o un `process.env.SECRETO` movido a `NEXT_PUBLIC_SECRETO` para "que
funcione en el cliente".

Excepción legítima: `NEXT_PUBLIC_FIREBASE_API_KEY` — la API key web de Firebase **es** pública por
diseño (la seguridad la dan `firestore.rules` + Auth, no el secreto de la key). El resto de las
`NEXT_PUBLIC_FIREBASE_*` también son config pública. Todo lo demás con `SECRET`/`TOKEN`/`PRIVATE`/
`PASSWORD` en el nombre bajo `NEXT_PUBLIC_` es un finding (Critical si es un secreto real).

## <a id="reglas"></a>Reglas de manejo de secretos

- Nunca hardcodear API keys/passwords/tokens en archivos commiteados (memoria del proyecto). Solo vía
  env. Si se necesita en código, leer de `process.env` (o `@/lib/env-config`).
- Secretos solo server-side. El cliente recibe datos ya procesados por una ruta API, nunca la credencial.
- No loguear secretos (ver [firestore.md](firestore.md) §PII).

## <a id="deps"></a>Dependencias

- Auditar con `npm audit` (el repo usa npm). Revisar al agregar una dependencia nueva: ¿es mantenida?,
  ¿cuántos transitive deps trae?, ¿hay CVEs conocidas? (`npm audit --production` para foco en runtime).
- No subir el floor de severidad: si `npm audit` ya tiene findings preexistentes, no introducir nuevos.
- Una dependencia nueva que se usa para procesar input de usuario (parsers, image libs) merece más
  escrutinio — son superficie de ataque.
