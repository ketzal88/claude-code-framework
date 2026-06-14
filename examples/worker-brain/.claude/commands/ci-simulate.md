---
description: Simulate exactly what GitHub Actions CI runs — 6 steps, all-or-nothing report
---

Run the exact same checks as `.github/workflows/quality-check.yml`, in order,
reporting all failures at once (same `if: always()` behaviour as CI).

```bash
# 1. TypeScript
npx tsc --noEmit 2>&1 | tail -30
echo "--- tsc exit: $?"

# 2. ESLint
npm run lint 2>&1 | tail -30
echo "--- lint exit: $?"

# 3. Alert engine tests
npm run test:alerts 2>&1 | tail -20
echo "--- test:alerts exit: $?"

# 4. Unit tests
npm run test:unit 2>&1 | tail -20
echo "--- test:unit exit: $?"

# 5. Firestore indexes JSON parse
python -c "import json; json.load(open('firestore.indexes.json')); print('indexes.json OK')"
echo "--- indexes exit: $?"

# 6. Error-reporting audit (advisory — always exits 0)
find src/app/api -type f \( -name 'route.ts' -o -name 'route.tsx' \) -print0 \
  | xargs -0 -n1 node scripts/check-error-reporting.js 2>&1 | grep -v "^$"
echo "--- audit done"
```

Después de correr todos los steps, reportar:
- ✅ PASS / ❌ FAIL para cada step
- Si hay fallos: el output completo del step que falló + qué fix aplicar
- Si todo pasa: "CI-ready — safe to push"

Use `NODE_OPTIONS=--max-old-space-size=6144` como hace CI.
