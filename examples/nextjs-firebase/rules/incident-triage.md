# Triage de incidentes — protocolo + diccionario de errores conocidos

14 sesiones de la auditoría 2026-07 arrancaron con el operador pegando texto crudo
(Slack de crons, logs de Vercel, mails de GitHub, issues de Sentry) y varios
turnos de reconstrucción de contexto — incluyendo errores YA diagnosticados
antes. Esta regla corta ese ciclo.

## Protocolo: cuando llega un error pegado (o "algo falló")

1. **Buscar primero en el diccionario de abajo.** Si matchea, ir directo a la
   causa+fix conocida — no re-derivar.
2. **Leer la señal estructurada antes de especular** (nunca el MCP de firebase):
   ```bash
   # Últimos ERROR de system_events + corridas de cron_executions
   npx tsx --require ./scripts/load-env.cjs -e "
   (async()=>{const {db}=require('./src/lib/firebase-admin');
   const ev=await db.collection('system_events').orderBy('timestamp','desc').limit(15).get();
   ev.docs.forEach(d=>{const x=d.data();if((x.severity||'').toUpperCase().includes('ERROR'))console.log(x.timestamp?.toDate?.()||x.timestamp,x.source||x.type,'-',String(x.message||'').slice(0,160))});
   const cr=await db.collection('cron_executions').orderBy('startedAt','desc').limit(10).get();
   cr.docs.forEach(d=>{const x=d.data();console.log('[cron]',x.cronName||x.name,x.status,x.startedAt?.toDate?.()||'')})})()"
   ```
3. Si es error de UI en producción: `mcp__claude_ai_Vercel__get_runtime_errors`.
4. **Al cerrar el diagnóstico de un error NUEVO: agregar su fila al diccionario
   en este mismo archivo, en el mismo turno.** La regla es viva.

## Diccionario de errores conocidos (causa → fix)

| Patrón del error | Causa | Fix / dónde mirar |
|---|---|---|
| `Apify API error 402: not-enough-usage-to-run-paid-actor` / `403 platform-feature-disabled` | Free tier del pool Apify agotado | Ver `getApifyUsageByAccount` (src/lib/scrapping/apify-tokens.ts); sumar token a `APIFY_EXTRA_TOKENS`; el candado pool-aware saltea el scan — no es bug del cron |
| Meta `Application request limit reached` (#17, #80004) | Rate limit de la Marketing API | Esperar la ventana (no reintentar en loop); si es sync masivo, chunkear por cuenta |
| Meta `#200` en portal OAuth | Permisos: la app necesita `ads_read` en Advanced Access + app Live | memoria reference_portal_meta_oauth_scope |
| `AUTH_REVOKED` / 401 en Shopify o TN | Token caído — el cliente desinstaló o rotó credenciales | Avisar a el operador para re-OAuth del cliente afectado (caso ClientA: 2 semanas sin sync). TN 404 "Last page is 0" NO es esto — es respuesta benigna de página vacía |
| Notion `validation ... select option does not exist` | La opción/propiedad no existe en la DB de Notion (schema cambió) | Revisar la DB en Notion; el código debe degradar elegante, no romper |
| Firestore `The query requires an index` | Falta índice compuesto | Agregarlo a `firestore.indexes.json` + `/deploy-indexes` — NUNCA crearlo desde el link de la consola |
| `firebase login --reauth` / credentials no longer valid | Vía equivocada (CLI interactivo) | Usar la vía service-account: `npx tsx --require ./scripts/load-env.cjs` (ver windows-environment.md) |
| Notion MCP `rate_limited 429` en import masivo | Fetches MCP interactivos para operación bulk | Script con API directa + backoff (ver regla de destilación en folder-organization.md) |
| GitHub `Quality Check: All jobs have failed ... in 2 seconds` | Falla de setup del workflow (npm ci / checkout), no del código | Ver el log del run con `gh run view`; no buscar el bug en el código todavía |
| UI prod `Cannot read properties of undefined (reading 'X')` | Fetch sin guard: `r.json()` sin chequear `r.ok`, acceso anidado sin `?.` | memoria feedback_fetch_ok_guard; buscar el fetch del componente que crasheó |
| Cron corrió pero "no pasó nada" (0 envíos, 0 docs) | Candado de idempotencia ya tomado, o filtro que excluyó todo | Ver el doc del candado del día (ej: `scrapping_outreach_runs/{id}__{fecha}`) y los filtros del pipeline — el run "verde" no garantiza output |
