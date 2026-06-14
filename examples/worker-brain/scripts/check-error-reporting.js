#!/usr/bin/env node
// Validates that API routes use withErrorReporting() / reportError().
// Cron routes additionally must call validateCronSecret().
// Emits a non-blocking advisory message on stderr when violations are found.
//
// Usage: node scripts/check-error-reporting.js <path-to-route-file>
// Always exits 0 (advisory only).

const fs = require("fs");
const path = require("path");

const filePath = process.argv[2];
if (!filePath) process.exit(0);

const norm = filePath.replace(/\\/g, "/");
if (!norm.includes("/src/app/api/")) process.exit(0);
if (!norm.endsWith("/route.ts") && !norm.endsWith("/route.tsx")) process.exit(0);

let source;
try {
    source = fs.readFileSync(filePath, "utf8");
} catch {
    process.exit(0);
}

const isCron = norm.includes("/src/app/api/cron/");
const issues = [];

const hasWrapper = /withErrorReporting\s*\(/.test(source);
const hasReportError = /reportError\s*\(/.test(source);
const hasCronSecret = /validateCronSecret\s*\(/.test(source);
const exportsHandler = /export\s+(?:const|async\s+function)\s+(GET|POST|PUT|PATCH|DELETE)/.test(source);

if (!exportsHandler) process.exit(0);

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

const swallow = /catch\s*\([^)]*\)\s*\{[^}]*console\.error[^}]*\}/g;
let m;
while ((m = swallow.exec(source))) {
    const block = m[0];
    if (!/reportError|withErrorReporting|throw\b/.test(block)) {
        issues.push("catch-block uses only console.error — error swallowed");
        break;
    }
}

if (issues.length === 0) process.exit(0);

const rel = path.relative(process.cwd(), filePath).replace(/\\/g, "/");
const lines = [
    "",
    "\u2192 [error-reporting] " + rel,
    ...issues.map((i) => "  - " + i),
    "  Fix: import { withErrorReporting } from '@/lib/error-reporter';",
    "       export const POST = withErrorReporting('source-name', async (req) => { /* logic */ });",
    "",
];
process.stderr.write(lines.join("\n"));
process.exit(0);
