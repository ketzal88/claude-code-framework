# Thresholds Regionales — Nunca Asumir Escala USD

Esta codebase opera con clientes en Argentina (ARS) cuyos valores de métricas son
órdenes de magnitud distintos a los de cuentas en USD.

## Los números que cambian con moneda

| Métrica         | USD típico | ARS típico (2025-2026) |
|----------------|------------|------------------------|
| ROAS            | 2–8x       | 50–500x                |
| CPA             | $5–$150    | $1.000–$50.000         |
| Gasto diario    | $50–$5.000 | $50.000–$5.000.000     |
| Revenue/orden   | $30–$300   | $30.000–$300.000       |

## Dónde están los thresholds en esta codebase

- `src/lib/parity-validators.ts` — `ROAS_IMPLAUSIBLE = 500` (no 100 — aprendido en bug)
- `src/lib/alert-engines/meta-alert-engine.ts` — targets de CPA vienen del `engine_config` del cliente (correcto — son por-cliente)
- `src/lib/financial-intelligence-service.ts` — MER benchmarks (>2.5 bueno, >4 excelente) son adimensionales ✓

## Regla

**Nunca hardcodear un threshold que dependa de escala de precios.**
Si el valor compara contra revenue, spend, CPA, o ROAS:
1. ¿Viene de `engine_config` del cliente? → OK (ya es por-cliente)
2. ¿Es adimensional (ratio, porcentaje, ratio de ratios)? → OK
3. ¿Es un valor absoluto en moneda? → Debe leer la moneda del cliente o usar percentiles relativos

## Cuando se activa esta regla

- Al escribir cualquier validador de parity (`parity-validators.ts`)
- Al agregar thresholds en alert engines
- Al definir "implausible" o "anormal" para cualquier métrica financiera
- Al agregar KPIs nuevos al financial dashboard

## Qué hacer cuando no tenés el currency del cliente

Si el cliente no tiene `currency` en su config, asumir ARS como default conservador
(el threshold más permisivo). Nunca asumir USD.
