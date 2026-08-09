#!/usr/bin/env node
// Validates that API routes use withErrorReporting() / reportError().
// Cron routes additionally must call validateCronSecret().
// Emits a non-blocking advisory message on stderr when violations are found.
//
// Usage:
//   node scripts/check-error-reporting.js <path-to-route-file>   → un archivo (hook PostToolUse)
//   node scripts/check-error-reporting.js                        → escanea src/app/api entero (CI)
//
// Always exits 0 (advisory only).
//
// El modo sin argumentos existe porque el barrido de CI con `find | xargs -n1` pasaba
// paths RELATIVOS y el filtro de abajo exigía "/src/app/api/" con barra inicial: el
// script salía en silencio en los 420 archivos y el step figuraba verde sin haber
// leído ninguno. Ahora el path se resuelve a absoluto ANTES de filtrar, y el modo
// barrido imprime siempre cuántos inspeccionó — un check que nunca dice nada es
// indistinguible de un check roto.

const fs = require("fs");
const path = require("path");

const API_DIR = path.join("src", "app", "api");

/** @returns {string[]|null} lista de issues (vacía = ok, null = archivo fuera de scope) */
function inspect(filePath) {
    // Resolver a absoluto primero: el filtro de scope compara contra "/src/app/api/",
    // que nunca matchea un path relativo tipo "src/app/api/x/route.ts".
    const norm = path.resolve(filePath).replace(/\\/g, "/");
    if (!norm.includes("/src/app/api/")) return null;
    if (!norm.endsWith("/route.ts") && !norm.endsWith("/route.tsx")) return null;

    let source;
    try {
        source = fs.readFileSync(filePath, "utf8");
    } catch {
        return null;
    }

    const isCron = norm.includes("/src/app/api/cron/");
    const issues = [];

    const hasWrapper = /withErrorReporting\s*\(/.test(source);
    const hasReportError = /reportError\s*\(/.test(source);
    const hasCronSecret = /validateCronSecret\s*\(/.test(source);
    const exportsHandler = /export\s+(?:const|async\s+function)\s+(GET|POST|PUT|PATCH|DELETE)/.test(source);

    if (!exportsHandler) return null;

    if (isCron && !hasCronSecret) {
        issues.push("MISSING validateCronSecret() (rules/cron-security.md)");
    }

    if (!hasWrapper && !hasReportError) {
        issues.push(
            isCron
                ? "MISSING withErrorReporting / reportError — cron errors will not reach Slack"
                : "MISSING withErrorReporting / reportError — silent failures will not reach Slack"
        );
    }

    // Un catch que devuelve 5xx sin reportar es el hueco que el wrapper NO tapa: el
    // handler nunca throwea, así que withErrorReporting no se entera. El cliente ve
    // un 500 y no queda rastro en ningún lado. Escape hatch para los casos legítimos
    // (config faltante, que es determinística y ya avisa al usuario):
    //   // error-reporting-exempt: <por qué>
    for (const block of catchBlocks(source)) {
        if (/reportError|withErrorReporting|throw\b|error-reporting-exempt/.test(block)) continue;
        if (/console\.error/.test(block)) {
            issues.push("catch-block uses only console.error — error swallowed");
        } else if (/status:\s*5\d\d/.test(block)) {
            issues.push("catch-block returns 5xx without reportError — silent server error");
        }
    }

    return issues;
}

/** Cuerpos de cada `catch {...}`, contando llaves anidadas (un `NextResponse.json({...})` las tiene). */
function catchBlocks(source) {
    const blocks = [];
    for (const m of source.matchAll(/catch\s*(\([^)]*\))?\s*\{/g)) {
        const open = m.index + m[0].length - 1;
        let depth = 0;
        for (let i = open; i < source.length; i++) {
            if (source[i] === "{") depth++;
            else if (source[i] === "}") {
                depth--;
                if (depth === 0) { blocks.push(source.slice(open, i + 1)); break; }
            }
        }
    }
    return blocks;
}

function report(filePath, issues) {
    const rel = path.relative(process.cwd(), filePath).replace(/\\/g, "/");
    process.stderr.write([
        "",
        "→ [error-reporting] " + rel,
        ...issues.map((i) => "  - " + i),
        "  Fix: import { withErrorReporting } from '@/lib/error-reporter';",
        "       export const POST = withErrorReporting('source-name', async (req) => { /* logic */ });",
        "",
    ].join("\n"));
}

function walk(dir, out = []) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) walk(full, out);
        else if (entry.name === "route.ts" || entry.name === "route.tsx") out.push(full);
    }
    return out;
}

const arg = process.argv[2];

if (arg) {
    const issues = inspect(arg);
    if (issues && issues.length > 0) report(arg, issues);
    process.exit(0);
}

// ── Modo barrido (CI) ───────────────────────────────────────────────────
if (!fs.existsSync(API_DIR)) {
    process.stderr.write(`[error-reporting] no existe ${API_DIR} — corriendo desde el directorio equivocado?\n`);
    process.exit(0);
}

let inspected = 0;
let withIssues = 0;
for (const file of walk(API_DIR)) {
    const issues = inspect(file);
    if (issues === null) continue;
    inspected++;
    if (issues.length > 0) {
        withIssues++;
        report(file, issues);
    }
}

// El canario: si esto dice 0 inspeccionadas, el check está roto — no limpio.
process.stderr.write(
    `\n[error-reporting] ${inspected} rutas inspeccionadas, ${withIssues} con hallazgos\n`
);
process.exit(0);
