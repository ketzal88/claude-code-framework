---
description: Review staged changes, auto-fix lint, run full CI checks, then commit
---

Perform a safe commit checkpoint. Goal: commit only code that would pass CI.

Steps:
1. Run `git status` and `git diff --stat` to see what's changed.

2. **ESLint auto-fix** (elimina errores de lint fixables antes de que lleguen a CI):
   ```bash
   npx eslint --fix "src/**/*.{ts,tsx}" --quiet 2>&1 | tail -20
   ```
   Anota qué archivos cambiaron para incluirlos en el commit.

3. Si algún archivo bajo `src/lib/alert-engines/` fue modificado:
   ```bash
   npx tsx --require ./scripts/load-env.cjs scripts/test-alert-engine.ts
   ```
   STOP si falla algún test.

4. `npx tsc --noEmit` — STOP si hay errores TypeScript.

5. `npm run lint` — STOP si hay errores de lint que no se auto-corrigieron.

6. `npm run test:unit` — STOP si fallan tests unitarios.

7. `python -c "import json; json.load(open('firestore.indexes.json'))"` — STOP si el JSON está roto.

8. **any-count ratchet**: `node scripts/check-any-baseline.js`
   - STOP si exits 1 (se agregaron nuevos `any`).
   - Si el count bajó, capturar el delta y correr `node scripts/count-any.js --baseline`.

9. **Dead-code**: `npm run check:dead-code` — STOP si creció el conteo de orphans.

10. Mostrar resumen del diff y proponer commit message (escanear `git log --oneline -10` para seguir el estilo).

11. Esperar confirmación del usuario antes de commitear.

12. Al confirmar:
    - Stagear solo archivos específicos (NUNCA `git add -A`).
    - Commit con HEREDOC + trailer `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`.
    - `git status` para verificar.

Safety:
- Nunca `--amend` sin instrucción explícita.
- Nunca `--no-verify`.
- Nunca incluir `.env*`, `*credentials*`, `*secret*`.
- SKIP_PREPUSH=1 SOLO está permitido cuando TODOS los archivos modificados son
  .md / .claude/ / docs/ (matching CI paths-ignore). Jamás para cambios de código.
- Si el pre-commit hook falla, fix y crear UN NUEVO commit (no amend).