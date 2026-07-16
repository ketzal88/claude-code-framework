# Entorno Windows — vía canónica vs vía prohibida

En esta máquina hay UNA vía que funciona para cada operación y una vía "default"
que falla siempre. Esta tabla existe porque el agente re-eligió la vía rota en
19 sesiones (auditoría 2026-07), quemando 1-3 turnos cada vez. El hook
`scripts/pre-bash-canonical-guard.py` bloquea las 4 más frecuentes con el fix
en el mensaje; esta regla es la referencia completa.

| Operación | USAR SIEMPRE | NUNCA USAR (por qué) |
|---|---|---|
| Lint | `npm run lint` · fix: `npx next lint --fix` | `npx eslint` / `eslint .` — resuelve al ESLint 9 global, que exige `eslint.config.js` y este repo usa `.eslintrc` vía `next lint` |
| Firestore reads/writes/scripts | `npx tsx --require ./scripts/load-env.cjs scripts/...` (service account, **nunca vence**) | Tools `mcp__plugin_firebase_*` y `firebase login` — el CLI pide reauth interactivo y muere headless (falló 6/6 veces) |
| Deploy de índices | `npx tsx --require ./scripts/load-env.cjs scripts/ops/deploy-firestore-indexes.ts --apply` | `firebase deploy --only firestore:indexes` (mismo problema de login) |
| Parsear JSON en shell | `node -e "const d=JSON.parse(require('fs').readFileSync(0,'utf8')); ..."` o Python | `jq` — no está instalado |
| Commit multilínea | PowerShell here-string `@'...'@` (cierre en columna 0) o `git commit -F archivo` | `git commit -m "línea1\nlínea2"` — los `\n` quedan literales |
| Cmdlets PS (`Select-Object`, `Get-Content`, `$env:`…) | Tool **PowerShell** | Tool Bash — sintaxis PS en Bash es error de parseo (y viceversa: `&&`/ternarios no existen en PS 5.1) |
| Variables en PowerShell | `$env:VAR = 'x'; cmd` · ojo: `$PID` es **readonly** | `VAR=x cmd` (idioma bash) · reasignar `$PID` |
| Scripts Python de hooks | Mensajes **ASCII-only** (sin acentos/ñ) o `PYTHONUTF8=1` | Acentos crudos → mojibake cp1252 en consola |
| Dev server para smoke tests | `node scripts/ops/dev-up.mjs` (reusa el vivo, mata huérfanos, levanta si falta) | `npm run dev` a ciegas — duplica servers en 3001/3002/3003 y deja huérfanos |
| Playwright MCP con "Browser is already in use" | Reintentar con `--isolated` | Reintentar igual N veces |

**Regla de oro:** si un comando falla con un error de autenticación interactiva,
config faltante o "command not found", NO reintentar variantes — buscar la fila
de esta tabla. Si el gotcha es nuevo, agregarlo acá en el mismo turno.
