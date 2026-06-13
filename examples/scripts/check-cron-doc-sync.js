#!/usr/bin/env node
// Doc-sync gate: verifies the CLAUDE.md cron table stays a mirror of the cron
// source of truth (.github/workflows/crons.yml). Catches the documented drift
// vector "added/renamed/removed a cron but forgot the table".
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

// CLAUDE.md is tracked lowercase on disk (`.claude/claude.md`); fall back across
// casings so this works on case-sensitive CI too.
const CLAUDE_MD_CANDIDATES = [
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

function resolveClaudeMd() {
    for (const candidate of CLAUDE_MD_CANDIDATES) {
        if (fs.existsSync(candidate)) return candidate;
    }
    process.stderr.write("check-cron-doc-sync: CLAUDE.md not found.\n");
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
    const claudeMd = resolveClaudeMd();

    const inWorkflow = extractEndpoints(CRONS_YML);
    const inDocs = extractEndpoints(claudeMd);

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

    process.stderr.write("\n✗ cron doc-sync DRIFT — CLAUDE.md cron table is out of sync with crons.yml\n");
    if (undocumented.length > 0) {
        process.stderr.write("  in crons.yml but MISSING from the CLAUDE.md table:\n");
        undocumented.forEach(n => process.stderr.write(`    + ${n}\n`));
    }
    if (stale.length > 0) {
        process.stderr.write("  in the CLAUDE.md table but GONE from crons.yml:\n");
        stale.forEach(n => process.stderr.write(`    - ${n}\n`));
    }
    process.stderr.write("\n  Fix the cron table in .claude/CLAUDE.md (it must mirror crons.yml).\n");
    process.stderr.write("  If an endpoint is an intentional exception, add it to IGNORE in this script.\n\n");
    process.exit(1);
}

main();
