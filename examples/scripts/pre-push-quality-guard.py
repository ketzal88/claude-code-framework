#!/usr/bin/env python
"""PreToolUse hook for Bash `git push`.

Mirrors your CI pipeline step-by-step so failures surface BEFORE the push,
not minutes later in a Slack notification.

HOW TO CONFIGURE:
1. Edit the CHECKS list below to match your CI steps exactly.
2. Set TIMEOUT_SEC high enough for your slowest check.
3. Commit this file and reference it from .claude/settings.json PreToolUse Bash hook.

SKIP_PREPUSH=1 BYPASS RULES:
- Allowed ONLY when ALL changed files match CI_PATHS_IGNORE patterns
  (e.g., docs, config, markdown — files CI would skip anyway).
- NOT allowed for any .ts/.tsx/.js code changes.
- The guard enforces this automatically.

Input contract (stdin JSON from Claude Code harness):
    { "tool_input": { "command": "git push ..." }, ... }
"""
import json
import os
import re
import subprocess
import sys
import time

# ── Configuration ─────────────────────────────────────────────────────────────
# Adapt these to match your CI pipeline exactly.
TIMEOUT_SEC = 300   # total budget across all checks; raise if lint/tsc is slow

CHECKS = [
    # (display-name, shell-command)
    # Mirror your CI steps exactly. Common for Next.js + TypeScript:
    ("tsc",         "npx tsc --noEmit"),
    ("lint",        "npm run lint"),
    ("test:unit",   "npm run test:unit"),
    # If you have additional CI steps, add them here:
    # ("test:e2e",  "npm run test:e2e"),
    # ("indexes",   "python -c \"import json; json.load(open('firestore.indexes.json'))\""),
]

# Files matching these patterns are ignored by CI (paths-ignore in your workflow).
# SKIP_PREPUSH=1 is only allowed when ALL changed files match this list.
CI_PATHS_IGNORE = [
    r"\.md$",
    r"^\.claude/",
    r"^docs/",
    r"^\.gitignore$",
    r"^\.gitattributes$",
]

# Node options to mirror CI environment (avoids OOM on ubuntu-latest with large TS codebases).
CI_MIRROR_ENV = {
    "NODE_OPTIONS": "--max-old-space-size=6144",
}
# ── End configuration ──────────────────────────────────────────────────────────

# React hooks that require "use client" in Next.js App Router components.
CLIENT_HOOKS_PATTERN = re.compile(
    r"\b(useState|useEffect|useRef|useCallback|useMemo|useContext|useReducer|useLayoutEffect)\s*[(<]"
)
USE_CLIENT_PATTERN = re.compile(r"""^['"]use client['"]""", re.MULTILINE)

TAIL_LINES = 40


def tail(text, n):
    lines = text.splitlines()
    return lines[-n:] if len(lines) > n else lines


def changed_files():
    """Files changed vs origin/main (falls back to HEAD~1)."""
    for cmd in [
        ["git", "diff", "--name-only", "origin/main...HEAD"],
        ["git", "diff", "--name-only", "HEAD~1"],
    ]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip().splitlines()
        except Exception:
            pass
    return []


def all_docs_only(files):
    """True if every changed file would be skipped by CI (safe to bypass)."""
    if not files:
        return False
    return all(any(re.search(p, f) for p in CI_PATHS_IGNORE) for f in files)


def check_use_client(project_root):
    """
    Find .tsx components that use React hooks but are missing 'use client'.
    These will fail Next.js build when imported from a Server Component.
    Returns list of (relative_path, hooks_found) tuples.
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
            rel_dir = dirpath.replace("\\", "/")
            if "/api/" in rel_dir:
                continue   # API routes are Server Components by design
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
            # All changes are docs/config that CI would skip — safe to bypass.
            return 0
        sys.stderr.write(
            "[pre-push] SKIP_PREPUSH=1 rejected: changed files include code.\n"
            "  SKIP_PREPUSH=1 is only allowed when ALL changes are docs/config\n"
            "  (matching CI paths-ignore). Fix the failing checks or push with --no-verify.\n"
        )
        return 2

    failures = []
    remaining = TIMEOUT_SEC

    for name, check_cmd in CHECKS:
        if remaining <= 2:
            failures.append((name, "skipped (timeout budget exhausted)", ""))
            continue

        start = time.monotonic()
        try:
            result = subprocess.run(
                ["bash", "-c", check_cmd],
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=remaining,
                env={**os.environ, **CI_MIRROR_ENV},
            )
        except subprocess.TimeoutExpired:
            failures.append((name, "timed out", ""))
            remaining = 0
            continue
        except FileNotFoundError:
            sys.stderr.write("[pre-push] bash not found — skipping quality guard.\n")
            return 0

        remaining = max(0, int(remaining - (time.monotonic() - start)))
        if result.returncode != 0:
            out = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
            failures.append((name, f"exit {result.returncode}", out))

    # Next.js "use client" boundary check (catches Vercel build failures tsc misses).
    uc = check_use_client(project_root)
    if uc:
        lines = ["Components using React hooks without \"use client\" — will fail Next.js build:"]
        for rel, hooks in uc[:10]:
            lines.append(f"  {rel}  [{', '.join(hooks[:3])}]")
        failures.append(("use-client", "missing directive", "\n".join(lines)))

    if not failures:
        return 0

    sys.stderr.write(f"[pre-push] {len(failures)} check(s) failed — blocking push:\n\n")
    for name, status, output in failures:
        sys.stderr.write(f"--- {name} ({status}) ---\n")
        for ln in tail(output, TAIL_LINES):
            sys.stderr.write(f"  {ln}\n")
        sys.stderr.write("\n")
    sys.stderr.write(
        "Fix the issues above, then push again.\n"
        "Docs-only bypass: SKIP_PREPUSH=1 git push ...\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
