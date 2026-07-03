#!/usr/bin/env node
// Dead-code ratchet: runs knip, compares findings vs .dead-code-baseline.json.
// Exits 1 if total grew OR any per-file count grew.
// Exits 0 otherwise. Same pattern as scripts/check-any-baseline.js.
//
// Usage:
//   node scripts/check-dead-code-baseline.js            -> ratchet check
//   node scripts/check-dead-code-baseline.js --write    -> write baseline
//   node scripts/check-dead-code-baseline.js --json     -> print current counts as JSON

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const REPO_ROOT = process.cwd();
const BASELINE_PATH = path.join(REPO_ROOT, ".dead-code-baseline.json");
const KNIP_VERSION = require(path.join(REPO_ROOT, "node_modules", "knip", "package.json")).version;

const CATEGORIES = [
    "files",
    "dependencies",
    "devDependencies",
    "exports",
    "types",
    "enumMembers",
    "classMembers",
    "duplicates",
    "unlisted",
    "binaries",
    "unresolved",
    "namespaceMembers",
];

function runKnip() {
    const r = spawnSync(
        "npx",
        ["knip", "--reporter", "json", "--no-progress"],
        { cwd: REPO_ROOT, encoding: "utf8", shell: true, maxBuffer: 50 * 1024 * 1024 },
    );
    // Knip exits 1 when it finds issues — that's not an error for us.
    if (r.status !== 0 && r.status !== 1) {
        process.stderr.write("knip failed to run:\n" + (r.stderr || "") + "\n");
        process.exit(2);
    }
    let data;
    try {
        data = JSON.parse(r.stdout);
    } catch (e) {
        process.stderr.write("knip produced invalid JSON: " + e.message + "\n");
        process.exit(2);
    }
    return data;
}

function aggregate(knipOutput) {
    const byCategory = Object.fromEntries(CATEGORIES.map(c => [c, 0]));
    const perFile = {};
    let total = 0;
    for (const issue of knipOutput.issues || []) {
        let fileTotal = 0;
        for (const c of CATEGORIES) {
            const n = (issue[c] || []).length;
            byCategory[c] += n;
            fileTotal += n;
        }
        if (fileTotal > 0) {
            // Normalize path separators for cross-platform stability.
            const key = issue.file.replace(/\\/g, "/");
            perFile[key] = (perFile[key] || 0) + fileTotal;
        }
        total += fileTotal;
    }
    return { total, byCategory, perFile };
}

function writeBaseline(current) {
    const today = new Date().toISOString().slice(0, 10);
    const out = {
        total: current.total,
        generatedAt: today,
        knipVersion: KNIP_VERSION,
        byCategory: current.byCategory,
        perFile: current.perFile,
    };
    fs.writeFileSync(BASELINE_PATH, JSON.stringify(out, null, 2) + "\n");
    process.stdout.write(
        `✓ wrote ${BASELINE_PATH} — total=${current.total}, ` +
        `files=${current.byCategory.files}, ` +
        `exports=${current.byCategory.exports}, ` +
        `types=${current.byCategory.types}, ` +
        `deps=${current.byCategory.dependencies + current.byCategory.devDependencies}\n`,
    );
}

function loadBaseline() {
    if (!fs.existsSync(BASELINE_PATH)) {
        process.stderr.write(
            "check-dead-code-baseline: .dead-code-baseline.json not found.\n" +
            "Run `npm run dead-code-baseline` once to create it.\n",
        );
        process.exit(1);
    }
    return JSON.parse(fs.readFileSync(BASELINE_PATH, "utf8"));
}

function main() {
    const args = process.argv.slice(2);
    const knipOutput = runKnip();
    const current = aggregate(knipOutput);

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

    // Scope-by-diff (auditoría 2026-07): when the Stop hook passes the list of
    // files THIS session touched (CHANGED_FILES, newline-separated, /-normalized),
    // only regressions in those files BLOCK. Regressions inherited from other
    // sessions' WIP downgrade to a warning — the global floor is still enforced
    // by CI, which runs without CHANGED_FILES and keeps the strict behavior.
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
        out.write(blocking ? `✗ dead-code ratchet FAILED\n` : `⚠ dead-code ratchet: solo deuda heredada (no bloquea)\n`);
        out.write(`  total: ${baseline.total} → ${current.total} (${totalDelta >= 0 ? "+" : ""}${totalDelta})\n`);
        if (own.length > 0) {
            out.write(`  files with new dead code (regresión TUYA — bloquea):\n`);
            own.sort((a, b) => b.delta - a.delta)
                .forEach(r => out.write(`    ${r.file}: ${r.prev} → ${r.now} (+${r.delta})\n`));
        }
        if (inherited.length > 0) {
            out.write(`  deuda heredada de otra sesión (warning, no bloquea acá; CI la enforcea):\n`);
            inherited.sort((a, b) => b.delta - a.delta)
                .forEach(r => out.write(`    ${r.file}: ${r.prev} → ${r.now} (+${r.delta})\n`));
        }
        out.write("\n");
        if (blocking) {
            out.write("  Fix: run `npx knip` to see per-file details, then either\n");
            out.write("    - delete the orphan export/file/dep, OR\n");
            out.write("    - wire it up to a real consumer if intentional.\n");
            out.write("  If you cleaned up OTHER files and the total dropped, regenerate:\n");
            out.write("    `npm run dead-code-baseline`\n\n");
            process.exit(1);
        }
        process.exit(0);
    }

    if (totalDelta < 0) {
        process.stdout.write(
            `✓ dead-code: ${baseline.total} → ${current.total} (${totalDelta}) — ` +
            `run \`npm run dead-code-baseline\` to lower the floor before committing.\n`,
        );
    } else {
        process.stdout.write(`✓ dead-code unchanged at ${current.total}.\n`);
    }
    process.exit(0);
}

main();
