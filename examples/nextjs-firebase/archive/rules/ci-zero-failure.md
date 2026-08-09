# CI Zero-Failure — Taxonomía completa de qué falla dónde y cómo prevenirlo

El objetivo es que `git push → CI verde` sea invariante. No "probablemente pase",
sino garantía estructural. Esto requiere entender exactamente qué falla dónde.

---

## Mapa de checks: quién detecta qué

| Problema | tsc | lint | test:alerts | test:unit | indexes | Vercel | use-client check |
|---|---|---|---|---|---|---|---|
| Error TypeScript | ✅ | - | - | - | - | ✅ | - |
| console.error en lib/api | - | ✅ | - | - | - | ✗ | - |
| import desconectado / any nueva | ✅ | ✅ | - | - | - | ✅ | - |
| Alert engine roto | - | - | ✅ | - | - | ✗ | - |
| Función pura rota | - | - | - | ✅ | - | ✗ | - |
| firestore.indexes.json malformado | - | - | - | - | ✅ | ✗ | - |
| "use client" faltante con hooks | - | - | - | - | - | ✅ | ✅ |
| Server Component usando browser API | - | - | - | - | - | ✅ | (parcial) |

✅ = lo detecta | ✗ = no lo detecta | - = no aplica

---

## Reglas por categoría

### TypeScript
- `tsc --noEmit` debe pasar en 0 errores antes de cada push.
- `ignoreBuildErrors: false` en `next.config.js` — los errores TypeScript fallan Vercel.
- Vercel y CI usan `NODE_OPTIONS=--max-old-space-size=6144` — el pre-push guard lo replica.
- **Trampa común:** types que son correctos en el editor pero fallan en CI porque el `tsconfig`
  de CI es más estricto. Correr `npx tsc --noEmit` localmente (no confiar solo en el editor).

### ESLint
- `eslint.ignoreDuringBuilds: true` — ESLint NO corre en el build de Vercel. Solo falla CI.
- Regla `no-console` como `error` en `src/lib/**` y `src/app/api/**`.
- **Fix antes de check**: correr `npx eslint --fix "src/**/*.{ts,tsx}"` antes de verificar.
  Muchos errores son auto-fixables (import order, trailing spaces, etc.).
- Ver `.claude/rules/console-error-pattern.md` para el patrón de console.error.

### Alert engine tests
- Tests puros, sin DB. Siempre deberían pasar si no se tocó alert-engines/.
- Cuando se agrega un alert type nuevo, agregar test en el MISMO commit.
- Nunca agregar un tipo de alert sin su test correspondiente — regla del alert-engine-pattern.md.

### Unit tests
- Tests de `src/lib/` funciones puras (date-utils, etc.).
- Si se modifica una función testeada, correr tests antes de commitear.

### firestore.indexes.json
- Se rompe si se edita manualmente o si hay un merge conflict no resuelto.
- El check es un simple `json.load()` — si falla, el archivo tiene un typo de JSON.
- El pre-push guard ahora lo incluye (era el gap más fácil de corregir).

### "use client" / Server-Client boundary (Vercel-only failure)
- Cualquier `.tsx` que use React hooks (`useState`, `useEffect`, etc.) SIN `"use client"`
  puede fallar el build de Vercel si es importado desde un Server Component.
- ESLint no lo detecta. tsc no lo detecta. Solo falla en `next build`.
- El pre-push guard ahora incluye un scan para esto.
- **Regla preventiva:** Todo componente que use hooks lleva `"use client"` en la primera línea.
  No depender de que "el padre lo tiene" — ser explícito.

---

## El SKIP_PREPUSH=1 — cuándo está permitido

SOLO cuando TODOS los archivos modificados son:
- `**.md`
- `.claude/**`
- `docs/**`
- `.gitignore` / `.gitattributes`

Esto espeja exactamente el `paths-ignore` de CI. Si CI lo ignoraría, SKIP_PREPUSH es seguro.
Para cualquier cambio de código `.ts/.tsx`, está PROHIBIDO usar SKIP_PREPUSH.
El guard ahora verifica esto y rechaza el bypass si hay archivos de código en el diff.

---

## El ciclo correcto antes de cada push

```
1. eslint --fix  →  auto-corrige errores fixables
2. tsc --noEmit  →  cero errores TypeScript
3. npm run lint  →  cero errores ESLint
4. test:alerts   →  si tocaste alert-engines/
5. test:unit     →  si tocaste funciones testeadas
6. indexes parse →  si tocaste firestore.indexes.json
```

O simplemente: usar `/commit-checkpoint` que corre todo esto en orden.

---

## Cuando CI falla y el pre-push pasó

Esto indica una diferencia de entorno. Causas conocidas:
1. **Archivo generado localmente que no se commiteó** (ej: un tipo generado, un archivo de config)
2. **Dependencia instalada localmente pero no en package.json** — `npm ci` falla en CI
3. **Variable de entorno usada en tiempo de build** que existe localmente pero no en CI
4. **Race condition en un test** que es flaky solo en CI — añadir `--retry 2` al test runner

Si CI falla consistentemente pero el pre-push pasa: agregar el check específico al pre-push guard.
