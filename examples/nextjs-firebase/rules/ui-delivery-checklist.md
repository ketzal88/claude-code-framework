# Entrega de UI

El patrón más caro: declarar UI "lista" sin abrirla, y que el QA lo termine haciendo el operador
defecto por defecto. El Stop hook `stop-ui-smoke-guard.py` bloquea el cierre si tocaste `.tsx`
sin ninguna llamada Playwright en la sesión.

## Antes de decir "listo"

1. **Página nueva** → llega a `<AppLayout>` y **está cableada en la navegación**. Una feature
   que no está en el menú no existe para el equipo (pasó 2 veces).
2. **Componente con fetch async** → rama explícita de empty state ("todavía no hay datos"), no
   solo skeleton (pasó 3 veces en un día).
3. **Usa hooks** → `"use client"` en la línea 1. No depender de que el padre lo tenga.
4. **Superficie con espejo** → muchas viven en 2-3 lados (panel / portal / público `/p/*`).
   Tocar una obliga a revisar las otras o listar explícitamente cuáles quedan pendientes.
   Cuidado con filtrar contexto interno al portal.
5. **Todo en español**, sin JSON crudo ni jerga interna a la vista del operador. Cada KPI nuevo
   con tooltip (qué mide y cómo se calcula) y texto de ayuda donde la UI pueda confundir.
   Antes de reescribir el label de una métrica, verificar qué calcula de verdad.
6. **Formularios públicos**: mobile-first.

## Smoke test

```bash
node scripts/ops/dev-up.mjs   # imprime DEV_URL= (reusa el server vivo o levanta uno)
```

Navegar la superficie tocada, mínimo 1 screenshot, verificar el checklist en el DOM real. El
middleware `isLocalDev` bypasea auth en localhost: para probar flujos de auth reales usar
`page.route()` mocks. Si el cambio es genuinamente invisible (refactor, tipos), cerrar con
`SKIP_SMOKE=1` y decirlo.

**Subagentes que implementan UI**: pegarles este checklist y exigir que no reporten DONE sin
cumplirlo — un "DONE" de subagente se verifica contra la UI real, no contra su palabra.
