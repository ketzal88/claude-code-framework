#!/usr/bin/env python
"""PreToolUse hook for Bash `git push`: runs the same checks CI runs and blocks on failure.

Mirrors `.github/workflows/quality-check.yml` step-by-step so failures surface
BEFORE the push (not 5 minutes later in Slack):
  1. npx tsc --noEmit
  2. npm run lint
  3. npm run test:alerts
  4. npm run test:unit
  5. python -c "json.load(open('firestore.indexes.json'))"  ← mirrors CI step 5
  5b. npm run check:design    ← design-contract ratchet (mirrors CI)
  5c. npm run check:cron-doc  ← cron table ↔ crons.yml doc-sync (mirrors CI)
  6. "use client" check — components using React hooks without the directive
  7. sentrux gate — structural regression vs .sentrux/baseline.json (only if binary + baseline exist)

All checks run regardless of individual failures (matches CI's `if: always()`)
so every problem is visible in a single pass.

SKIP_PREPUSH=1 bypass rules:
  - Allowed: when ALL changed files match CI paths-ignore:
    **.md, .claude/**, docs/**, .gitignore, .gitattributes
  - NOT allowed for real code changes — the guard is your last line of defence.

Input contract (stdin JSON from Claude Code harness):
    { "tool_input": { "command": "git push ..." }, ... }
"""
import json
import os
import re
import subprocess
import sys
import time

TIMEOUT_SEC = 300  # raised from 240 — lint on large codebase can take 60s+
TAIL_LINES = 40

# CI paths-ignore patterns — SKIP_PREPUSH is only safe when ALL changes match these
CI_PATHS_IGNORE = [
    r"\.md$",
    r"^\.claude/",
    r"^docs/",
    r"^\.gitignore$",
    r"^\.gitattributes$",
]

CHECKS = [
    ("tsc",         "npx tsc --noEmit"),
    ("lint",        "npm run lint"),
    ("test:alerts", "npm run test:alerts"),
    ("test:unit",   "npm run test:unit"),
    ("indexes.json", "python -c \"import json; json.load(open('firestore.indexes.json'))\""),
    ("design",      "npm run check:design"),
    ("cron-doc",    "npm run check:cron-doc"),
]

CI_MIRROR_ENV = {
    "NODE_OPTIONS": "--max-old-space-size=6144",
}

# sentrux gate — opt-in structural regression check.
# Skips silently when the binary or the baseline isn't present, so this hook
# stays portable for anyone who hasn't installed sentrux yet.
SENTRUX_BIN = os.environ.get("SENTRUX_BIN", r"C:\tmp\sentrux\sentrux.exe")
SENTRUX_BASELINE = os.path.join(".sentrux", "baseline.json")

# Hooks that are missing "use client" but use React hooks — causes Vercel build failures.
# Pattern: file has useState|useEffect etc but NOT "use client" at the top.
CLIENT_HOOKS_PATTERN = re.compile(
    r"\b(useState|useEffect|useRef|useCallback|useMemo|useContext|useReducer|useLayoutEffect)\s*[(<]"
)
USE_CLIENT_PATTERN = re.compile(r"""^['"]use client['"]""", re.MULTILINE)


def tail(text, n):
    lines = text.splitlines()
    return lines[-n:] if len(lines) > n else lines


def changed_files():
    """Return list of files changed vs origin/main (or HEAD if no remote)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "origin/main...HEAD"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip().splitlines()
    except Exception:
        pass
    return []


def all_docs_only(files):
    """Return True if every changed file matches CI paths-ignore (safe to skip)."""
    if not files:
        return False  # unknown — don't skip
    for f in files:
        if not any(re.search(pat, f) for pat in CI_PATHS_IGNORE):
            return False
    return True


def check_use_client(project_root):
    """
    Scan src/components and src/app (non-api) for .tsx files that use React hooks
    but are missing the "use client" directive.
    Returns list of (filepath, hooks_found) tuples.
    """
    violations = []
    search_dirs = [
        os.path.join(project_root, "src", "components"),
        os.path.join(project_root, "src", "app"),
    ]
    for base in search_dirs:
        if not os.path.isdir(base):
            continue
        for dirpath, _, filenames in os.walk(base):
            # Skip API routes — they're Server Components by design
            if "/api/" in dirpath.replace("\\", "/"):
                continue
            for fname in filenames:
                if not fname.endswith(".tsx"):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    content = open(fpath, encoding="utf-8", errors="replace").read()
                except Exception:
                    continue
                hooks = CLIENT_HOOKS_PATTERN.findall(content)
                if hooks and not USE_CLIENT_PATTERN.search(content):
                    rel = os.path.relpath(fpath, project_root).replace("\\", "/")
                    violations.append((rel, list(set(hooks))))
    return violations


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    cmd = (payload.get("tool_input", {}) or {}).get("command", "") or ""

    if not re.match(r"^\s*git\s+push(\s|$)", cmd):
        return 0

    if "--dry-run" in cmd or "--no-verify" in cmd:
        return 0

    if os.environ.get("SKIP_PREPUSH") == "1":
        files = changed_files()
        if all_docs_only(files):
            # All changes are docs/config → CI would skip them too → safe to bypass
            return 0
        # Code changes: refuse bypass — guard must run
        sys.stderr.write(
            "[pre-push] SKIP_PREPUSH=1 rejected: changed files include non-docs code.\n"
            "  SKIP_PREPUSH=1 is only allowed when ALL changes are .md / .claude/ / docs/\n"
            "  (matching CI paths-ignore). Fix the checks or push --no-verify manually.\n"
        )
        return 2

    failures = []
    remaining = TIMEOUT_SEC

    for name, check_cmd in CHECKS:
        if remaining <= 2:
            failures.append((name, "skipped (budget exhausted)", ""))
            continue

        start = time.monotonic()
        try:
            result = subprocess.run(
                ["bash", "-c", check_cmd],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=remaining,
                env={**os.environ, **CI_MIRROR_ENV},
            )
        except subprocess.TimeoutExpired:
            failures.append((name, "timed out", ""))
            remaining = 0
            continue
        except FileNotFoundError:
            sys.stderr.write("[pre-push] bash not found on PATH -- skipping quality guard.\n")
            return 0

        elapsed = time.monotonic() - start
        remaining = max(0, int(remaining - elapsed))

        if result.returncode != 0:
            combined = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
            failures.append((name, "exit " + str(result.returncode), combined))

    # "use client" check — lightweight, no subprocess needed
    uc_violations = check_use_client(project_root)
    if uc_violations:
        lines = ["Components using React hooks without \"use client\" — will fail Vercel build:"]
        for rel, hooks in uc_violations[:10]:
            lines.append("  " + rel + "  [" + ", ".join(hooks[:3]) + "]")
        failures.append(("use-client", "missing directive", "\n".join(lines)))

    # sentrux gate — structural regression vs .sentrux/baseline.json.
    # Skip silently if not configured (binary missing OR baseline missing).
    if os.path.isfile(SENTRUX_BIN) and os.path.isfile(SENTRUX_BASELINE):
        try:
            result = subprocess.run(
                [SENTRUX_BIN, "gate", project_root],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            if result.returncode != 0:
                combined = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
                failures.append(("sentrux", "structural regression", combined))
        except subprocess.TimeoutExpired:
            failures.append(("sentrux", "timed out (>30s)", ""))
        except Exception as e:
            # Don't block the push on infrastructure errors — log and continue.
            sys.stderr.write("[pre-push] sentrux gate skipped: " + str(e) + "\n")

    if not failures:
        return 0

    sys.stderr.write(
        "[pre-push] " + str(len(failures)) + " check(s) failed -- blocking `git push`:\n\n"
    )
    for name, status, output in failures:
        sys.stderr.write("--- " + name + " (" + status + ") ---\n")
        for ln in tail(output, TAIL_LINES):
            sys.stderr.write("  " + ln + "\n")
        sys.stderr.write("\n")
    sys.stderr.write(
        "Fix the issues above, then push again.\n"
        "Bypass only for docs-only changes: SKIP_PREPUSH=1 git push ...\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
