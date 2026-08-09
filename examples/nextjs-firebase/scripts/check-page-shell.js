#!/usr/bin/env node
// Shell gate: verifies every page of the internal panel reaches <AppLayout>.
//
// Why this exists: this repo has no route-group layout for the panel. The root
// `src/app/layout.tsx` only mounts providers — the chrome (sidebar, header, and
// the `max-w-[1400px] mx-auto` work area) lives in `@/components/layouts/AppLayout`,
// which every page has to remember to wrap itself in. A page that forgets it does
// NOT fail: it renders full-bleed at the viewport width, with no sidebar and no
// padding. Nothing throws, nothing warns — it just looks broken. That silent
// failure has shipped on essentially every new section (last: /anuncios).
//
// The shell may sit anywhere in the render tree (the house pattern is
// `page.tsx` -> `components/pages/X.tsx` -> AppLayout), so this follows imports
// instead of only grepping the page file.
//
// Exit 1 (with a report) if any non-exempt page can't reach the shell, else 0.
//
// Usage:
//   node scripts/check-page-shell.js              -> check every panel page (CI)
//   CHANGED_FILES="a.tsx b.tsx" node ...          -> only report pages in that set
//   node scripts/check-page-shell.js --list       -> print the verdict for every page

const fs = require("fs");
const path = require("path");

const REPO_ROOT = process.cwd();
const APP_DIR = path.join(REPO_ROOT, "src", "app");
const SHELL_IMPORT = /from\s+["'](?:@\/components\/layouts\/AppLayout|.*\/layouts\/AppLayout)["']/;

// How many import hops to follow before giving up. The real chains are 1-2
// (page -> components/pages/X -> maybe a per-objective sub-view); 4 is slack.
const MAX_DEPTH = 4;

// ── Exemption 1: surfaces that are NOT the internal panel ────────────────────
// These have their own shell (portal, academia) or are `brand` register on
// purpose (public reports, marketing tools, landing). See DESIGN.md.
const EXEMPT_PREFIXES = [
    "api/",             // route handlers, not pages
    "portal/",          // own shell: src/app/portal/layout.tsx
    "academia/",        // own shell: src/app/academia/layout.tsx
    "public/",          // brand: public reports
    "tools/",           // brand: public tools
    "herramientas/",    // brand: public lead-gen calculators (SEO metadata, no login)
    "landing/",         // brand: marketing
    "lite/",            // brand: marketing
    "p/",               // brand: public report short links
    "w/",               // brand: public short links
    "login/",
    "privacy/",
    "terms/",
    "authorize/",
    "select-account/",
    "onboarding/",
];

// ── Exemption 3 (explicit escape hatch) ──────────────────────────────────────
// A page can opt out by stating why, in the file itself:
//   // shell-exempt: <reason>
const ESCAPE_HATCH = /\/\/\s*shell-exempt:/;

/** Exemption 1 — path-based. */
function isExemptPath(rel) {
    return EXEMPT_PREFIXES.some((p) => rel.startsWith(p));
}

/**
 * Exemption 2a — a redirect-only page. It renders nothing, so it has no layout
 * to get wrong. Matches both the server (`redirect()`) and client
 * (`router.replace()` in an effect, returning null) idioms.
 */
function isRedirectOnly(src) {
    const serverRedirect = /from\s+["']next\/navigation["']/.test(src) && /\bredirect\s*\(/.test(src);
    const clientRedirect = /router\.(replace|push)\s*\(/.test(src) && /return\s+null\s*;?\s*}/.test(src);
    // Guard: a real page can also call redirect() on an auth failure branch and
    // still render UI. Only treat it as redirect-only if there is no JSX beyond
    // the bare `return null`.
    const hasRealJsx = /return\s*\(\s*</.test(src);
    return (serverRedirect || clientRedirect) && !hasRealJsx;
}

/**
 * Exemption 2b — a deliberate full-screen surface. `fixed inset-0` on the ROOT
 * element means the page takes over the viewport on purpose: a canvas editor,
 * not a document. Adding the panel chrome around it would be the bug.
 * Real case: /admin/proposals/[slug]/edit.
 *
 * Anchored to `return ( <div className="…fixed inset-0…"` on purpose: a bare
 * search for the class matches any MODAL rendered inside a perfectly normal
 * page (/admin/users, /admin/proposals, …) and would silently exempt pages that
 * do have the shell — a gate that reports OK without looking is worse than no
 * gate. Pages with a shell never reach this check anyway (see verdictFor).
 */
function isFullScreen(src) {
    return /return\s*\(\s*<div[^>]*className=["'][^"']*fixed\s+inset-0/.test(src);
}

function listPages(dir, out = []) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) listPages(full, out);
        else if (entry.name === "page.tsx") out.push(full);
    }
    return out;
}

/** Resolve an import specifier (`@/x` or `./x`) to a file on disk. */
function resolveImport(spec, fromFile) {
    let base;
    if (spec.startsWith("@/")) base = path.join(REPO_ROOT, "src", spec.slice(2));
    else if (spec.startsWith(".")) base = path.resolve(path.dirname(fromFile), spec);
    else return null; // node_modules — can't hold our shell

    for (const ext of [".tsx", ".ts", path.join("index.tsx"), path.join("index.ts")]) {
        const candidate = base.endsWith(ext) ? base : base + ext;
        if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) return candidate;
    }
    return null;
}

/** Walk the import graph looking for the shell. Returns true as soon as it's found. */
function reachesShell(file, depth = MAX_DEPTH, seen = new Set()) {
    if (depth < 0 || seen.has(file) || !fs.existsSync(file)) return false;
    seen.add(file);

    const src = fs.readFileSync(file, "utf8");
    if (SHELL_IMPORT.test(src)) return true;

    for (const match of src.matchAll(/from\s+["']([^"']+)["']/g)) {
        const next = resolveImport(match[1], file);
        if (next && reachesShell(next, depth - 1, seen)) return true;
    }
    return false;
}

function verdictFor(file) {
    const rel = path.relative(APP_DIR, file).split(path.sep).join("/");
    if (isExemptPath(rel)) return { rel, status: "exempt", why: "superficie brand / con shell propio" };

    // The shell is checked BEFORE the heuristic exemptions: a page that reaches
    // AppLayout is correct by definition, and asking the heuristics first let a
    // modal's `fixed inset-0` exempt 6 healthy pages from the gate entirely.
    if (reachesShell(file)) return { rel, status: "ok", why: "llega a AppLayout" };

    const src = fs.readFileSync(file, "utf8");
    if (ESCAPE_HATCH.test(src)) return { rel, status: "exempt", why: "shell-exempt declarado en el archivo" };
    if (isRedirectOnly(src)) return { rel, status: "exempt", why: "redirect, no renderiza" };
    if (isFullScreen(src)) return { rel, status: "exempt", why: "full-screen deliberado (fixed inset-0)" };

    return { rel, status: "broken", why: "no llega a AppLayout" };
}

function main() {
    const listAll = process.argv.includes("--list");

    // Scope-by-diff: the Stop hook passes the files THIS session touched, so
    // inherited debt from another session warns instead of blocking. CI runs
    // without it and enforces globally. Mirrors the dead-code/design ratchets.
    const changed = (process.env.CHANGED_FILES || "")
        .split(/\s+/)
        .filter(Boolean)
        .map((f) => f.split(path.sep).join("/"));
    const scoped = changed.length > 0;

    const verdicts = listPages(APP_DIR).map(verdictFor);

    if (listAll) {
        for (const v of verdicts.sort((a, b) => a.status.localeCompare(b.status) || a.rel.localeCompare(b.rel))) {
            console.log(`${v.status.toUpperCase().padEnd(7)} ${v.rel.padEnd(52)} ${v.why}`);
        }
        return;
    }

    let broken = verdicts.filter((v) => v.status === "broken");
    if (scoped) {
        broken = broken.filter((v) => changed.some((c) => c.endsWith(`src/app/${v.rel}`)));
    }

    if (broken.length === 0) {
        const scopeNote = scoped ? " (alcance: archivos de esta sesion)" : "";
        console.log(`OK: todas las paginas del panel llegan a AppLayout${scopeNote}.`);
        return;
    }

    console.error("");
    console.error(`FALLA: ${broken.length} pagina(s) del panel sin shell (AppLayout).`);
    console.error("");
    for (const v of broken) console.error(`  - src/app/${v.rel}`);
    console.error("");
    console.error("Sin AppLayout la pagina renderiza a lo ancho del viewport, sin sidebar");
    console.error("ni padding: se sale del layout. No tira error, solo se ve rota.");
    console.error("");
    console.error("Como arreglarlo:");
    // Mensajes ASCII-only a proposito: la consola de esta maquina es cp1252 y
    // cualquier acento sale mojibake (ver .claude/rules/windows-environment.md).
    console.error('  1. Envolver lo que devuelve la pagina en <AppLayout>:');
    console.error('       import AppLayout from "@/components/layouts/AppLayout";');
    console.error("     (o dejarlo en el componente de components/pages/ que ya use)");
    console.error("  2. Si NO es panel (superficie brand/publica): sumar su prefijo a");
    console.error("     EXEMPT_PREFIXES en scripts/check-page-shell.js.");
    console.error("  3. Si es full-screen a proposito, o alguna otra excepcion real:");
    console.error("       // shell-exempt: <por que>");
    console.error("");
    process.exit(1);
}

main();
