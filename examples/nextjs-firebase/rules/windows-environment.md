# Entorno Windows — vía canónica vs vía que falla

Para cada operación hay una vía que funciona y una vía "default" que falla siempre. El hook
`scripts/pre-bash-canonical-guard.py` bloquea las más frecuentes con el fix en el mensaje.

| Operación | USAR | NUNCA (por qué) |
|---|---|---|
| Lint | `npm run lint` · fix: `npx next lint --fix` | `npx eslint` — resuelve al ESLint 9 global, que exige `eslint.config.js`; el repo usa `.eslintrc` vía `next lint` |
| Firestore (reads/writes/scripts) | `npx tsx --require ./scripts/load-env.cjs scripts/…` — service account, nunca vence | Tools `mcp__*firebase*` y `firebase login` — piden reauth interactivo y mueren headless |
| Deploy de índices | `npx tsx --require ./scripts/load-env.cjs scripts/ops/deploy-firestore-indexes.ts --apply` | `firebase deploy --only firestore:indexes` (mismo login) |
| Parsear JSON en shell | `node -e "…JSON.parse…"` o Python | `jq` — no está instalado |
| Commit multilínea | Here-string PS `@'…'@` (cierre en columna 0) o `git commit -F archivo` | `git commit -m "a\nb"` — los `\n` quedan literales |
| Cmdlets PS | Tool **PowerShell** | Tool Bash — y viceversa: `&&`, ternarios y `??` no existen en PS 5.1 |
| Variables de entorno | `$env:VAR = 'x'; cmd` · `$PID` es readonly | `VAR=x cmd` (idioma bash) |
| Hooks en Python | Mensajes ASCII-only o `PYTHONUTF8=1` | Acentos crudos → mojibake cp1252 |
| Dev server para smoke tests | `node scripts/ops/dev-up.mjs` (reusa el vivo, mata huérfanos) | `npm run dev` a ciegas — duplica servers y deja huérfanos |
| Playwright "Browser is already in use" | Reintentar con `--isolated` | Reintentar igual N veces |

**Regla:** si un comando falla por auth interactiva, config faltante o "command not found", no
reintentar variantes — buscar la fila. Si el gotcha es nuevo, agregarlo acá en el mismo turno.
