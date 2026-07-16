#!/usr/bin/env node
// PostToolUse advisory hook — runs after Claude edits a .ts/.tsx file.
// If the file's current any-count exceeds its baseline, prints a warning to
// stderr. Never blocks (always exits 0). The blocking gate lives in
// scripts/check-any-baseline.js (called from pre-push).

const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const REPO_ROOT = process.cwd();
const BASELINE_PATH = path.join(REPO_ROOT, ".any-baseline.json");

const filePath = process.argv[2];
if (!filePath) process.exit(0);

const norm = filePath.replace(/\\/g, "/");
if (!/\.(ts|tsx)$/.test(norm)) process.exit(0);

// Skip paths outside src/
const relFromRepo = path.relative(REPO_ROOT, filePath).replace(/\\/g, "/");
if (!relFromRepo.startsWith("src/")) process.exit(0);

if (!fs.existsSync(filePath)) process.exit(0);
if (!fs.existsSync(BASELINE_PATH)) process.exit(0);

const baseline = JSON.parse(fs.readFileSync(BASELINE_PATH, "utf8"));
const prev = baseline.perFile[relFromRepo] ?? 0;

const r = spawnSync(
    process.execPath,
    [path.join(REPO_ROOT, "scripts", "count-any.js"), "--file", filePath, "--json"],
    { cwd: REPO_ROOT, encoding: "utf8" },
);
if (r.status !== 0) process.exit(0);

let result;
try {
    result = JSON.parse(r.stdout);
} catch {
    process.exit(0);
}

const now = result.total;

if (now > prev) {
    const delta = now - prev;
    process.stderr.write("\n");
    process.stderr.write(`→ [no-new-any] ${relFromRepo}: ${prev} → ${now} (+${delta})\n`);
    process.stderr.write(`  Consider: \`unknown\` + type-guards (src/lib/type-guards.ts),\n`);
    process.stderr.write(`  typed interfaces (src/types/channel-rawdata.ts pattern), or Zod.\n`);
    process.stderr.write(`  pre-push will block this unless the count comes down elsewhere.\n\n`);
}

process.exit(0);
