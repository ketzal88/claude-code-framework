#!/usr/bin/env bash
# ExampleApp — security review triage (PRIMER PASE, no es verdad absoluta).
# Surface de candidatos de alta señal. CADA hit hay que verificarlo leyendo el código.
# No reemplaza la revisión manual; arranca con lo barato y determinístico.
#
# Uso (desde cualquier lado):  bash .claude/skills/security-review/scripts/triage.sh
set -uo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

echo "════════════════════════════════════════════════════════════"
echo " Security triage — ExampleApp"
echo " Cada hit = candidato, NO confirmación. Leer el código de cada uno."
echo "════════════════════════════════════════════════════════════"

echo ""
echo "── 1. Cron routes sin validateCronSecret ──────────────────────"
# Todo handler en src/app/api/cron/**/route.ts debe llamar validateCronSecret.
missing=0
while IFS= read -r f; do
  [ -z "$f" ] && continue
  if ! grep -q "validateCronSecret" "$f"; then
    echo "  ⚠ $f"
    missing=1
  fi
done < <(find src/app/api/cron -name 'route.ts' 2>/dev/null)
[ "$missing" -eq 0 ] && echo "  ✓ todos los crons llaman validateCronSecret"

echo ""
echo "── 2. Secretos expuestos vía NEXT_PUBLIC_ (van al browser) ─────"
# NEXT_PUBLIC_* se inlinea en el JS del cliente. Known-OK: FIREBASE_* (público por diseño).
hits=$(grep -rnE "NEXT_PUBLIC_[A-Z_]*(SECRET|PRIVATE|TOKEN|PASSWORD)" src/ 2>/dev/null | grep -vE "FIREBASE" || true)
if [ -n "$hits" ]; then echo "$hits" | sed 's/^/  ⚠ /'; else echo "  ✓ sin NEXT_PUBLIC_ con nombre de secreto en src/"; fi

echo ""
echo "── 3. console.error en lib/ o api/ (lint + posible info leak) ──"
hits=$(grep -rn "console\.error" src/lib src/app/api 2>/dev/null | grep -vE "error-reporter\.ts|firebase-admin\.ts|slack-service\.ts" || true)
if [ -n "$hits" ]; then echo "$hits" | sed 's/^/  ⚠ /'; else echo "  ✓ ninguno fuera de los 3 archivos de infra permitidos"; fi

echo ""
echo "── 4. set(...merge) con posible body crudo (mass-assignment) ──"
# Heurística: .set(x, { merge: true }) cerca de un req.json(). Falsos positivos esperables.
hits=$(grep -rnE "\.set\([^,]+,\s*\{\s*merge:\s*true" src/app/api 2>/dev/null || true)
if [ -n "$hits" ]; then echo "$hits" | sed 's/^/  ? /'; echo "  (verificar que el objeto pase por whitelist, no body crudo)"; else echo "  ✓ sin set+merge en rutas API"; fi

echo ""
echo "── 5. Rutas con clientId y CERO señal de auth (residual) ──────"
# La cobertura de authz NO es determinística por grep: este repo tiene varios modelos
# legítimos (sesión, token-en-path para /public, HMAC en webhooks, OAuth). Acá marcamos
# solo el RESIDUAL: rutas que tocan clientId y no muestran NINGUNA de esas señales.
# No es la lista de bugs — es la cola corta que mejor merece una lectura manual.
AUTH_SIGNALS="requireClientAccess|requirePortalSession|requireActivePortalClient|validateCronSecret|getAuthenticatedUser|isAllowedMcpEmail|ADMIN_UIDS|verifySessionCookie|cookies\.get|getServerSession|requireAdmin|auth\.verify|getAuthUser|session|token|createHmac|timingSafeEqual|hmac|signature|oauth|signed_request"
mapfile -t residual < <(
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    if grep -qE "clientId|params\.id" "$f" && ! grep -qiE "$AUTH_SIGNALS" "$f"; then echo "$f"; fi
  done < <(grep -rlE "clientId|params\.id" src/app/api --include='route.ts' 2>/dev/null)
)
total=$(grep -rlE "clientId|params\.id" src/app/api --include='route.ts' 2>/dev/null | wc -l | tr -d ' ')
if [ "${#residual[@]}" -eq 0 ]; then
  echo "  ✓ las $total rutas con clientId muestran alguna señal de auth"
else
  echo "  ${#residual[@]} de $total rutas con clientId sin señal de auth visible — leer cada una:"
  printf '  ? %s\n' "${residual[@]}" | head -20
  [ "${#residual[@]}" -gt 20 ] && echo "  … (+$(( ${#residual[@]} - 20 )) más; correr el grep para la lista completa)"
fi
echo "  (read-only de datos no sensibles puede ser intencional; verificar)"

echo ""
echo "════════════════════════════════════════════════════════════"
echo " Fin del triage. Próximo: leer las referencias por categoría"
echo " y verificar manualmente cada candidato."
echo "════════════════════════════════════════════════════════════"
