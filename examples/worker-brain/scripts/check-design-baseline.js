#!/usr/bin/env node
// Design-contract ratchet: scans product-register .tsx for DESIGN.md violations,
// compares vs .design-baseline.json. Exits 1 if total grew OR any per-file count grew.
// Exits 0 otherwise. Same pattern as scripts/check-dead-code-baseline.js.
//
// Enforces the three deterministic non-negotiables from DESIGN.md:
//   - boxShadow    : "Flat-Forever Rule" — no box-shadow anywhere (ratchet; 94-ish today).
//   - borderRadius : "zero radius across the system" except the spinner (hard-zero today).
//   - gradientText : gradient text is banned (hard-zero today).
//
// The accent-≤8% rule is NOT here — it is not statically distinguishable from a
// legitimate yellow button fill (665 `bg-classic` uses, almost all valid). That
// rule is covered by the on-demand visual audit in /design-gate (impeccable).
//
// Scope: only .tsx under src/, EXCLUDING `brand`-register surfaces (public reports,
// /tools/*, portal). Those are designed per-task and DESIGN.md explicitly says not
// to copy the terminal aesthetic there. We scan .tsx only (not .css) on purpose:
// Tailwind classes + inline styles live in .tsx, and the intentional spinner
// exception (`border-radius: 9999px` on `.animate-spin`) lives in globals.css.
//
// Usage:
//   node scripts/check-design-baseline.js            -> ratchet check
//   node scripts/check-design-baseline.js --write     -> write/refresh baseline
//   node scripts/check-design-baseline.js --json      -> print current counts as JSON

const fs = require("fs");
const path = require("path");

const REPO_ROOT = process.cwd();
const BASELINE_PATH = path.join(REPO_ROOT, ".design-baseline.json");
const SRC_ROOT = path.join(REPO_ROOT, "src");

// brand-register surfaces — exempt from the panel design contract.
// Matched against the forward-slash-normalized path relative to REPO_ROOT.
const BRAND_EXCLUDE = [
    "src/app/public/",
    "src/components/public/",
    "src/app/tools/",
    "src/app/portal/",
    "src/components/portal/",
];

// One regex per category. Each is applied with the global flag and the matches
// are counted. Patterns are intentionally narrow to avoid drifting false
// positives — a stable false positive is harmless (it is captured in the
// baseline), but a varying one would make the ratchet flaky.
// High-precision over high-recall: this gate BLOCKS the turn, so a false
// positive is worse than a miss. Every pattern below is an unambiguous Tailwind
// utility (or the gradient-clip signature) — no inline value-parsing, no
// backtracking lookaheads. The on-demand visual audit in /design-gate
// (impeccable) covers the semantic cases this deterministic tier intentionally
// skips (accent ≤8%, nonzero inline styles, hero-metric template).
const RULES = {
    // "Flat-Forever Rule" — Tailwind shadow utilities. `shadow-none` is the
    // opt-out and is NOT matched (not in the suffix list). box-shadow is NOT
    // neutralized by tailwind.config, so these render real shadows → real
    // violations.
    boxShadow: /\bshadow-(?:sm|md|lg|xl|2xl|inner)\b|\bshadow-\[/g,

    // "Zero-radius Rule" — only REAL radius is gated. Named utilities
    // (`rounded`, `rounded-lg`, even `rounded-full`) are neutralized to 0px by
    // tailwind.config.ts and are visually inert, so we do NOT flag them. What
    // produces actual radius is an ARBITRARY value — `rounded-[8px]` bypasses
    // the theme and renders the literal radius. `rounded-[0px]` is allowed. The
    // spinner exception lives in globals.css (.css is out of scope), so it never
    // trips this rule.
    borderRadius: /\brounded-\[(?!0(?:px|rem|em|%)?\])/g,

    // Gradient text is banned — emphasis is weight/size/classic color, never a
    // gradient over background-clip: text.
    gradientText: /\bbg-clip-text\b|\bbackground-clip\s*:\s*text|\bbackgroundClip\s*:\s*['"]text/g,
};

const CATEGORIES = Object.keys(RULES);

function isExcluded(relPath) {
    return BRAND_EXCLUDE.some(prefix => relPath.startsWith(prefix));
}

function collectTsxFiles(dir, acc) {
    let entries;
    try {
        entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
        return acc;
    }
    for (const entry of entries) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) {
            if (entry.name === "node_modules" || entry.name === ".next") continue;
            collectTsxFiles(full, acc);
        } else if (entry.isFile() && entry.name.endsWith(".tsx")) {
            acc.push(full);
        }
    }
    return acc;
}

function scan() {
    const byCategory = Object.fromEntries(CATEGORIES.map(c => [c, 0]));
    const perFile = {};
    let total = 0;

    const files = collectTsxFiles(SRC_ROOT, []);
    for (const abs of files) {
        const rel = path.relative(REPO_ROOT, abs).replace(/\\/g, "/");
        if (isExcluded(rel)) continue;

        let content;
        try {
            content = fs.readFileSync(abs, "utf8");
        } catch {
            continue;
        }

        let fileTotal = 0;
        for (const c of CATEGORIES) {
            const matches = content.match(RULES[c]);
            const n = matches ? matches.length : 0;
            byCategory[c] += n;
            fileTotal += n;
        }
        if (fileTotal > 0) {
            perFile[rel] = fileTotal;
            total += fileTotal;
        }
    }

    // Stable ordering so the baseline diff stays clean across machines.
    const orderedPerFile = {};
    for (const key of Object.keys(perFile).sort()) orderedPerFile[key] = perFile[key];

    return { total, byCategory, perFile: orderedPerFile };
}

function writeBaseline(current) {
    const today = new Date().toISOString().slice(0, 10);
    const out = {
        total: current.total,
        generatedAt: today,
        byCategory: current.byCategory,
        perFile: current.perFile,
    };
    fs.writeFileSync(BASELINE_PATH, JSON.stringify(out, null, 2) + "\n");
    process.stdout.write(
        `✓ wrote ${BASELINE_PATH} — total=${current.total}, ` +
        `boxShadow=${current.byCategory.boxShadow}, ` +
        `borderRadius=${current.byCategory.borderRadius}, ` +
        `gradientText=${current.byCategory.gradientText}\n`,
    );
}

function loadBaseline() {
    if (!fs.existsSync(BASELINE_PATH)) {
        process.stderr.write(
            "check-design-baseline: .design-baseline.json not found.\n" +
            "Run `npm run design-baseline` once to create it.\n",
        );
        process.exit(1);
    }
    return JSON.parse(fs.readFileSync(BASELINE_PATH, "utf8"));
}

function main() {
    const args = process.argv.slice(2);
    const current = scan();

    if (args.includes("--write")) {
        writeBaseline(current);
        process.exit(0);
    }

    if (args.includes("--json")) {
        process.stdout.write(JSON.stringify(current, null, 2) + "\n");
        process.exit(0);
    }

    const baseline = loadBaseline();

    const regressed = [];
    for (const [file, count] of Object.entries(current.perFile)) {
        const prev = baseline.perFile[file] ?? 0;
        if (count > prev) {
            regressed.push({ file, prev, now: count, delta: count - prev });
        }
    }

    const totalDelta = current.total - baseline.total;

    // Scope-by-diff (auditoría 2026-07): igual que check-dead-code-baseline.js —
    // con CHANGED_FILES seteado (Stop hook), solo bloquean las regresiones en
    // archivos que ESTA sesión tocó; lo heredado es warning. CI corre sin
    // CHANGED_FILES y mantiene el enforcement global estricto.
    const changedEnv = process.env.CHANGED_FILES;
    const changedSet = changedEnv
        ? new Set(changedEnv.split("\n").map(f => f.trim().replace(/\\/g, "/")).filter(Boolean))
        : null;
    const own = changedSet ? regressed.filter(r => changedSet.has(r.file)) : regressed;
    const inherited = changedSet ? regressed.filter(r => !changedSet.has(r.file)) : [];

    if (regressed.length > 0 || totalDelta > 0) {
        const blocking = own.length > 0 || !changedSet;
        const out = blocking ? process.stderr : process.stdout;
        out.write("\n");
        out.write(blocking ? "✗ design-contract ratchet FAILED\n" : "⚠ design-contract: solo deuda heredada (no bloquea)\n");
        out.write(`  total: ${baseline.total} → ${current.total} (${totalDelta >= 0 ? "+" : ""}${totalDelta})\n`);
        if (own.length > 0) {
            out.write("  files with new design violations (regresión TUYA — bloquea):\n");
            own.sort((a, b) => b.delta - a.delta)
                .forEach(r => out.write(`    ${r.file}: ${r.prev} → ${r.now} (+${r.delta})\n`));
        }
        if (inherited.length > 0) {
            out.write("  deuda heredada de otra sesión (warning, no bloquea acá; CI la enforcea):\n");
            inherited.sort((a, b) => b.delta - a.delta)
                .forEach(r => out.write(`    ${r.file}: ${r.prev} → ${r.now} (+${r.delta})\n`));
        }
        out.write("\n");
        if (blocking) {
            out.write("  DESIGN.md non-negotiables (panel/product register):\n");
            out.write("    - no box-shadow      → use tonal ramp + 1px argent border (shadow-none to opt out)\n");
            out.write("    - zero border-radius → drop rounded-* (rounded-full is allowed for dots/spinner)\n");
            out.write("    - no gradient text   → emphasis is weight/size/classic color\n");
            out.write("  If you cleaned up OTHER files and the total dropped, regenerate:\n");
            out.write("    `npm run design-baseline`\n\n");
            process.exit(1);
        }
        process.exit(0);
    }

    if (totalDelta < 0) {
        process.stdout.write(
            `✓ design-contract: ${baseline.total} → ${current.total} (${totalDelta}) — ` +
            "run `npm run design-baseline` to lower the floor before committing.\n",
        );
    } else {
        process.stdout.write(`✓ design-contract unchanged at ${current.total} violations.\n`);
    }
    process.exit(0);
}

main();
