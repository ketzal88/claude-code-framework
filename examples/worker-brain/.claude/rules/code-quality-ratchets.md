# Code Quality Ratchets — any, archivos grandes, código muerto

Tres ratchets activos en esta codebase. El floor nunca puede subir.

---

## 1. any-type ratchet

**Baseline actual:** ver `.dead-code-baseline.json` (campo `anyCount` o grep count).
**Comando de medición:**
```bash
grep -r ": any\b\|as any\b\|any\[\]\b" src/ --include="*.ts" --include="*.tsx" | wc -l
```

**Regla:**
- Cuando editás un archivo, no podés agregar más `any` de los que ya tiene.
- Si el archivo ya tiene `any`, podés dejarlos como están — pero no sumar.
- Si borrás `any` existentes (bien), actualizá el baseline: `npm run dead-code-baseline`.

**Orden de ataque (prioridad):**
1. Archivos con >20 instancias: `slack-service.ts` (refactored), `performance-service.ts`, `meta-sync-service.ts`
2. Bodies de request en rutas POST/PATCH: `const body = await req.json() as ConcreteType`
3. Callbacks de arrays con `(item: any)` → tipar con el tipo del array

**Nunca** escribir `any` solo porque es más fácil. Alternativas:
- `unknown` + type guard para inputs externos
- `Record<string, unknown>` para objetos dinámicos
- Crear un tipo concreto aunque sea incompleto (`Partial<...>`)
- `Parameters<typeof fn>[0]` para reusar tipos de funciones existentes

---

## 2. Archivos grandes (>800 líneas)

**Cuando editar un archivo que ya tiene >800 líneas:**
1. Verificar si la edición va a crecer el archivo más.
2. Si sí → dividir ANTES de agregar la nueva funcionalidad.
3. Si no → OK por ahora, pero abrir un comentario TODO para futuro split.

**Patrón de split:** un archivo grande casi siempre tiene sub-responsabilidades claras.
Ejemplo: `context-builder.ts` → `context-meta.ts`, `context-ecommerce.ts`, `context-email.ts`, etc.

**Señal de split necesario:** si el archivo tiene >3 secciones con comentarios tipo
`// ─── Meta ───`, `// ─── Email ───` → ya están definidos los módulos, solo falta separar.

**Comando para detectar archivos grandes:**
```bash
find src/ -name "*.ts" -o -name "*.tsx" | xargs wc -l | sort -rn | head -20
```

---

## 3. Código muerto (knip ratchet)

**Stop hook activo** — bloquea el turn si el orphan count creció.
**Baseline:** `.dead-code-baseline.json` (floor actual: 84).

**Antes de renombrar o refactorizar:**
```bash
grep -r "NombreViejo" src/ --include="*.ts" --include="*.tsx" -l
```
Verificar todos los call sites antes de asumir que solo vivía donde editaste.

**Antes de agregar un export nuevo:**
- ¿Va a ser consumido por alguien? Si no hay consumer inmediato, no exportar.
- Exportar solo cuando hay un import que lo usa. Nunca "por las dudas".

**Cuando el Stop hook bloquea:**
- Opción A: borrar el export huérfano (preferida)
- Opción B: conectarlo a un consumer real
- Opción C: si limpiaste otros archivos y el total bajó, `npm run dead-code-baseline`
- Bypass de emergencia: `SKIP_DEADCODE=1` (solo para docs-only changes)

---

## 4. Contrato de diseño (DESIGN.md ratchet)

**Stop hook activo** (`scripts/stop-design-guard.py`) — bloquea el turn si las violaciones
visuales crecen en alguna `.tsx` del register `product`/panel.
**Baseline:** `.design-baseline.json` (floor actual: 99 — 93 box-shadow + 6 border-radius arbitrario + 0 gradient-text).

**Qué enforça (las no-negociables determinísticas de DESIGN.md):**
- `box-shadow` (`shadow-sm/md/lg/xl/2xl/inner`, `shadow-[…]`) → Flat-Forever: depth via tonal ramp + 1px `border-argent`. Opt-out: `shadow-none`.
- border-radius **real** (`rounded-[…]` arbitrario) → zero-radius. Los `rounded-*` con nombre (incl. `rounded-full`) son inertes — `tailwind.config.ts` los cuadra a 0px, así que NO se flaggean. El spinner (`globals.css`) está exento.
- gradient-text (`bg-clip-text`) → el énfasis es weight/size/`text-classic`.

**Qué NO enforça (va a la auditoría visual, no es greppable):** el accent ≤8%. Un `bg-classic`
es legítimo en botón primario / active stripe / un KPI, pero una card amarilla es violación —
indistinguible por grep. Eso lo cubre `/design-gate` Tier 2 vía `/impeccable`.

**Scope:** solo register `product`. Exentas las superficies `brand`: `src/app/public/**`,
`src/components/public/**`, `src/app/tools/**`, `src/app/portal/**`, `src/components/portal/**`.

**Comandos:**
- `npm run check:design` — corre el ratchet, exit 1 si regresó.
- `npm run design-baseline` — regenera el baseline (solo cuando *bajaste* violaciones de verdad).
- `/design-gate` — versión manual completa (Tier 1 determinístico + Tier 2 visual con impeccable).

**Cuando el Stop hook bloquea:**
- Opción A: arreglar la violación en la `.tsx` (shadow→border, sacar `rounded-[…]`, sacar gradient-text).
- Opción B: si la superficie es `brand` de verdad, moverla bajo una ruta exenta.
- Opción C: si limpiaste otros archivos y el total bajó, `npm run design-baseline`.
- Bypass de emergencia: `SKIP_DESIGN=1` (solo para docs-only changes).

---

## Pre-commit self-check (para Claude)

Antes de proponer un commit, verificar mentalmente:
1. ¿Agregué `any`? → Justificar o eliminar
2. ¿El archivo editado tiene ahora >800 líneas? → Planificar split
3. ¿Renombré algo sin buscar todos los imports? → `grep -r OldName src/`
4. ¿Exporté algo que nadie importa? → Quitar el `export`
5. ¿Usé `console.error` fuera de los 3 archivos permitidos? → Cambiar a `reportError()`
6. ¿Agregué `box-shadow` / `rounded-[…]` / gradient-text en una `.tsx` del panel? → Romper el contrato de diseño; usar tonal ramp + border, sacar el radio/gradiente
