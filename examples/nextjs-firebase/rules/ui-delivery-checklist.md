# Entrega de UI — checklist determinístico + receta de smoke test

El patrón más caro detectado en la auditoría 2026-07 (20 sesiones): declarar UI
"lista" sin verificarla, y que el QA lo termine haciendo el operador a mano, defecto
por defecto. El Stop hook `scripts/stop-ui-smoke-guard.py` bloquea el cierre si
se tocaron `.tsx` de UI sin ninguna llamada Playwright en la sesión. Esta regla
documenta QUÉ verificar y CÓMO hacerlo barato.

## A. Checklist antes de declarar UI lista (verificable sin browser)

1. **¿Page/route nueva?** → debe estar cableada en la navegación (buscar el
   config de nav con `grep -r "href.*<ruta>" src/components/layouts src/configs`).
   Una feature invisible en el menú no existe para el equipo (pasó 2 veces).
2. **¿Componente con fetch async?** → rama explícita de **empty state**
   ("sin datos" / "estamos cargando tu tienda por primera vez"), no solo
   skeleton (pasó 3 veces en un día).
3. **¿Usa hooks React?** → `"use client"` en línea 1. No depender del padre.
4. **¿La superficie tiene espejo?** → muchas superficies existen en 2-3 lados
   (panel interno / portal cliente / público `/p/*`). Tocar una implica revisar
   si las otras muestran lo mismo — o listar explícitamente cuáles quedan
   pendientes. Ojo con fugas de contexto interno al portal
   ([[project_portal_internal_context_leak]]).
5. **Textos en español** + tooltip en todo KPI nuevo (qué mide, fórmula).

## B. Receta canónica de smoke test (1 comando + 1 navegación)

```bash
node scripts/ops/dev-up.mjs   # imprime DEV_URL= (reusa server vivo o levanta uno)
```

Después: navegar la superficie tocada con Playwright, sacar **mínimo 1
screenshot**, y verificar el checklist A en el DOM real. Gotchas conocidos:

- `Browser is already in use` → reintentar con `--isolated`.
- El middleware `isLocalDev` bypasea auth en localhost — para probar flujos de
  auth reales usar `page.route()` mocks (memoria feedback_playwright_smoke_tests).
- Nunca decir "listo para probar" sin haber corrido el browser. Si el cambio es
  genuinamente invisible (refactor, tipos), cerrar con `SKIP_SMOKE=1` y decirlo.

## C. Propagación a subagentes implementadores

Todo prompt a un subagente que implemente UI debe incluir el checklist A
verbatim y la instrucción: **no reportar DONE sin haberlo cumplido** (los
subagentes reportaron features inexistentes 3+ veces — el "DONE" de un subagente
se verifica contra la UI real, no contra su palabra).
