---
description: Simulate CI pipeline locally — all steps, all failures visible at once
---

Run every step of your CI pipeline locally. Mirror the `if: always()` behavior:
all steps run even if earlier ones fail, so you see the full failure picture.

Adapt the commands below to match your `.github/workflows/*.yml` exactly.

```bash
export NODE_OPTIONS="--max-old-space-size=6144"

echo "=== 1/5  TypeScript ===" && npx tsc --noEmit; TSC=$?
echo "=== 2/5  ESLint     ===" && npm run lint; LINT=$?
echo "=== 3/5  Unit tests ===" && npm run test:unit; UNIT=$?
echo "=== 4/5  Alert/pure ===" && npm run test:alerts 2>/dev/null || echo "(no test:alerts)"; ALERTS=$?
echo "=== 5/5  DB indexes ===" && python -c "import json; json.load(open('firestore.indexes.json')); print('OK')" 2>/dev/null || echo "(no firestore.indexes.json)"

echo ""
echo "Results:"
[ $TSC   -eq 0 ] && echo "  ✅ tsc"    || echo "  ❌ tsc"
[ $LINT  -eq 0 ] && echo "  ✅ lint"   || echo "  ❌ lint"
[ $UNIT  -eq 0 ] && echo "  ✅ tests"  || echo "  ❌ tests"

[ $TSC -eq 0 ] && [ $LINT -eq 0 ] && [ $UNIT -eq 0 ] \
  && echo "" && echo "CI-ready — safe to push" \
  || echo "" && echo "Fix failures above before pushing"
```

After running, report:
- ✅ / ❌ for each step
- Full output of any failing step
- What fix to apply (TypeScript error → fix types; lint → fix or `eslint --fix`; test → fix the test)
