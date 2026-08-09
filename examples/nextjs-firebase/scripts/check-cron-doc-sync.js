#!/usr/bin/env node
// Doc-sync gate: verifies the cron table stays a mirror of the cron source of
// truth (.github/workflows/crons.yml). Catches the documented drift vector
// "added/renamed/removed a cron but forgot the table".
//
// The table lives in the `worker-cron` SKILL (loaded on demand), not in
// CLAUDE.md — it is ~3.8k tokens of pure reference that used to be paid on
// every session. CLAUDE.md keeps only a pointer.
//
// Name-level comparison only (it does not check schedules or descriptions —
// those are reviewed by a human). Extracts every `/api/cron/<name>` endpoint
// from both files and diffs the two sets.
//
// Exit 1 (with a report) if they drift, exit 0 if in sync.
//
// Usage:
//   node scripts/check-cron-doc-sync.js          -> check, exit 1 on drift
//   node scripts/check-cron-doc-sync.js --json    -> print both sets as JSON

const fs = require("fs");
const path = require("path");

const REPO_ROOT = process.cwd();
const CRONS_YML = path.join(REPO_ROOT, ".github", "workflows", "crons.yml");

// Where the cron table lives, most-preferred first. The worker-cron skill is
// the real home; the CLAUDE.md entries stay as a fallback so the gate keeps
// working if the table is ever moved back (CLAUDE.md is tracked lowercase on
// disk, so both casings are listed for case-sensitive CI).
const DOC_CANDIDATES = [
    path.join(REPO_ROOT, ".claude", "skills", "worker-cron", "SKILL.md"),
    path.join(REPO_ROOT, ".claude", "claude.md"),
    path.join(REPO_ROOT, ".claude", "CLAUDE.md"),
];

// Endpoints that intentionally live in crons.yml but NOT as their own row in the
// CLAUDE.md cron table. Keep this list tight — every entry is a deliberate
// exception, not a convenience.
const IGNORE = new Set([
    "process-backfill-queue", // folded into the fill-gaps row ("includes process-backfill-queue")
    "daily-briefing",         // DEPRECATED, workflow_dispatch fallback only
    "weekly-alerts",          // DEPRECATED, workflow_dispatch fallback only
]);

const ENDPOINT_RE = /\/api\/cron\/([a-z0-9-]+)/g;

function extractEndpoints(file) {
    const text = fs.readFileSync(file, "utf8");
    const names = new Set();
    for (const match of text.matchAll(ENDPOINT_RE)) {
        if (!IGNORE.has(match[1])) names.add(match[1]);
    }
    return names;
}

function resolveDocFile() {
    for (const candidate of DOC_CANDIDATES) {
        if (fs.existsSync(candidate)) return candidate;
    }
    process.stderr.write("check-cron-doc-sync: cron table doc not found (looked for the worker-cron SKILL.md and CLAUDE.md).\n");
    process.exit(2);
}

function diff(a, b) {
    return [...a].filter(x => !b.has(x)).sort();
}

function main() {
    const args = process.argv.slice(2);

    if (!fs.existsSync(CRONS_YML)) {
        process.stderr.write("check-cron-doc-sync: .github/workflows/crons.yml not found.\n");
        process.exit(2);
    }
    const docFile = resolveDocFile();

    const inWorkflow = extractEndpoints(CRONS_YML);
    const inDocs = extractEndpoints(docFile);

    if (args.includes("--json")) {
        process.stdout.write(JSON.stringify({
            inWorkflow: [...inWorkflow].sort(),
            inDocs: [...inDocs].sort(),
        }, null, 2) + "\n");
        process.exit(0);
    }

    const undocumented = diff(inWorkflow, inDocs); // in crons.yml, missing from the table
    const stale = diff(inDocs, inWorkflow);        // in the table, gone from crons.yml

    if (undocumented.length === 0 && stale.length === 0) {
        process.stdout.write(`✓ cron doc-sync: ${inWorkflow.size} crons, table in sync.\n`);
        process.exit(0);
    }

    const rel = path.relative(REPO_ROOT, docFile).replace(/\\/g, "/");
    process.stderr.write(`\n✗ cron doc-sync DRIFT — the cron table in ${rel} is out of sync with crons.yml\n`);
    if (undocumented.length > 0) {
        process.stderr.write("  in crons.yml but MISSING from the table:\n");
        undocumented.forEach(n => process.stderr.write(`    + ${n}\n`));
    }
    if (stale.length > 0) {
        process.stderr.write("  in the table but GONE from crons.yml:\n");
        stale.forEach(n => process.stderr.write(`    - ${n}\n`));
    }
    process.stderr.write(`\n  Fix the cron table in ${rel} (it must mirror crons.yml).\n`);
    process.stderr.write("  If an endpoint is an intentional exception, add it to IGNORE in this script.\n\n");
    process.exit(1);
}

main();
