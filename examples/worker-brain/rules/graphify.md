# graphify — knowledge graph del codebase (wiring real de Worker Brain)

Espejo fiel de cómo está cableado graphify en producción (repo ai-analyzer /
Worker Brain, TypeScript/Next.js/Firebase). La versión portable/agnóstica vive en
`core/commands/graphify.md` + `core/rules/graphify.md`; esto documenta las
particularidades del stack real.

## Invocación (gotcha Windows real)

En la máquina de Worker Brain el `.exe` de graphify no se pudo escribir en
`C:\Python310\Scripts` (dir read-only + fuera de PATH), así que:
- Todo se invoca vía `python -m graphify <cmd>`.
- Hay shims manuales (`graphify` + `graphify.cmd` → `python -m graphify %*`) en
  `C:\Users\<user>\AppData\Local\Python\bin` (dir escribible ya en PATH), para que
  `graphify ...` resuelva en Git Bash y PowerShell.
- Los 3 hooks de `settings.json` usan `python -m graphify` a propósito (no dependen
  del shim).

## Grafo

- Construido sobre la RAÍZ del repo (`graphify update .`), no `src/`, para que los
  hooks de auto-consulta (que buscan `graphify-out/graph.json` en el CWD root) lo
  encuentren sin overrides. Build real: ~24.3k nodos / ~44.7k edges / ~1.35k
  comunidades (nombradas por su hub file, gratis — sin naming por LLM).
- `graphify-out/` gitignoreado. Los builds scopeados de un subsistema
  (`graphify update src/lib/X`) dejan su propio `graphify-out/` adentro de esa
  carpeta — también gitignoreados; limpiarlos si se acumulan.

## Hooks cableados (settings.json — modo agresivo)

- `PreToolUse` Bash → `python -m graphify hook-guard search`
- `PreToolUse` Read|Glob → `python -m graphify hook-guard read`
- `Stop` → `python scripts/stop-graphify-refresh.py` (refresh en background tras
  turnos con cambios de código; no bloquea el cierre)

## Reglas de uso (las que sigue el asistente)

1. Antes de explorar zona desconocida → `graphify query "<pregunta>"`, después leer
   solo lo que importa.
2. Antes de tocar un service/util compartido → `graphify explain "<nombre>"` para el
   blast radius. **El uso de mayor valor acá** — encaja con el bug recurrente del
   "checklist de 5 consumidores" al agregar un campo `Client`.
3. Trazar un flujo cron→engine→slack → `graphify path "<A>" "<B>"`.
4. Tras cambios grandes → `graphify update .` (o el Stop hook lo hace solo).

## Punto ciego (importante en este stack)

El grafo es de imports/AST — NO ve el acople runtime que define a Worker Brain:
cron→route por HTTP, colección `channel_snapshots` compartida entre services,
event flows. Las islas del grafo reflejan ese desacople real. Orientar con el grafo,
confirmar en el código — nunca tratarlo como análisis de impacto completo para
flujos Firestore/cron.
