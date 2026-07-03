# Operating Procedure — auto-routing (Claude elige la secuencia; el usuario NO invoca comandos)

El usuario de este repo **no tipea slash commands**. Claude elige y ejecuta la
secuencia correcta según el **tipo** y el **tamaño** del trabajo, y anuncia en una
línea qué eligió. La metodología es automática; los comandos (`/design-gate`,
`/audit-parity`, `/test-alerts`…) son la implementación de cada paso, no un botón
que el usuario tiene que apretar.

## Paso 0 — Triage por tamaño (SIEMPRE primero)

- **Trivial** — pregunta, lectura, explicación, cambio de 1-2 líneas sin lógica
  → responder directo. **Cero secuencia, cero ceremonia.** No abrir TodoWrite, no
  planificar, no correr gates. Hacerlo y listo.
- **Sustancial** — feature, refactor, fix con lógica, nueva UI, cambio de datos/sync
  → aplicar la secuencia de abajo que corresponda.

Meter ceremonia en lo trivial es el modo de falla opuesto y es igual de malo que
saltearla en lo sustancial. El default para una charla normal es **liviano**.

## Secuencias por tipo de trabajo (solo si es "sustancial")

| Si el trabajo es… | Claude corre, en orden |
|---|---|
| **Feature nueva no trivial** | Planificar inline primero: 1 línea de supuestos + las decisiones de dominio reales como A/B/C → implementar → cierre |
| **Cambio de UI (register `product`)** | Implementar → checklist + smoke-test de `ui-delivery-checklist.md` (`node scripts/ops/dev-up.mjs` + navegación Playwright; el Stop hook `stop-ui-smoke-guard.py` lo exige) → el ratchet de diseño ya corre solo al cerrar; tener presente accent ≤8% |
| **Alert nuevo/modificado** | `alert-engine-pattern` (pure `evaluate()` + test en el MISMO cambio) → `npm run test:alerts` → actualizar la tabla de alerts en CLAUDE.md |
| **Cron nuevo/modificado** | `validateCronSecret` + `withErrorReporting` + idempotencia → sincronizar `crons.yml` **y** la tabla de CLAUDE.md (el doc-sync lo verifica) |
| **Toca `channel_snapshots` / un sync** | Verificar paridad: doc-ID correcto, mismo campo que lee la UI; ante la duda, `/audit-parity` |
| **Cambio financiero / thresholds** | Escala ARS, nunca USD; todo threshold absoluto lee el `currency` del cliente |
| **Firestore: campo/colección nueva** | Campo opcional `?` + fallback en reads + `merge:true` en writes; índice compuesto ANTES de shippear |

## Protocolo de cierre (obligatorio en trabajo sustancial)

1. **Self-check de ratchets** de `code-quality-ratchets.md` (§pre-commit): tsc
   limpio, sin `any` nuevos, sin `console.error` en lib/api, sin código muerto,
   sin romper el contrato de diseño. Si tocaste algo testeado, correr ese test.
2. **Commitear sin que Gabriel lo pida.** Al terminar trabajo sustancial, correr
   la secuencia de `/commit-checkpoint` y commitear. Nunca cerrar un turno con
   working tree sucio sin explicitarlo (el Stop hook `stop-dirty-tree-guard.py`
   lo recuerda una vez). Si es WIP deliberado o deuda de otra sesión, decirlo.
3. **Línea de estado git SIEMPRE al final del mensaje:**
   `Estado git: commiteado <sha corto> — N commit(s) listos para que pushees`
   (o `sin cambios de código`). Gabriel no es developer: esa línea es todo lo
   que necesita para decidir pushear.
4. **NUNCA ejecutar `git push` ni intentar bypasses** (`--no-verify`,
   `SKIP_PREPUSH` para código). El deny es intencional: el push lo hace Gabriel
   a mano, siempre. Un worktree/branch que deba llegar a main se mergea
   fast-forward local a main y se reporta — jamás se pushea. (Excepción única:
   Gabriel lo pide explícitamente en el chat → `ALLOW_CLAUDE_PUSH=1`.)

Esto lo hace Claude por default — no espera que el usuario lo pida.

## Regla de oro

Anunciar la secuencia elegida en **una línea** ("Esto es UI → implemento y smoke-test
antes de cerrar") y seguirla. El usuario no maneja la metodología: la ve pasar y puede
cortarla cuando quiera. Ante la duda entre liviano y pesado para algo del medio,
elegir liviano y decir qué se saltea.
