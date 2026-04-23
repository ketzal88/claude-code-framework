#!/usr/bin/env python
"""Stop hook: runs the dead-code ratchet before Claude terminates a turn.

If the ratchet fails (new orphan exports/files/deps introduced), exits 2
with stderr so Claude sees the regression and is forced to clean up
before really finishing. Mirrors the philosophy of the any-ratchet:
the baseline is the floor, the count can only go down.

Skip conditions (all exit 0, no-op):
  - `stop_hook_active=True` in payload (this is a re-trigger from our own
    prior block — don't loop).
  - env `SKIP_DEADCODE=1` (explicit bypass).
  - no .ts/.tsx/.js changes in the working tree (nothing to check).
  - knip not installed yet (`.dead-code-baseline.json` missing or knip
    binary absent).
  - knip itself crashes or times out (we never want to block a turn
    because of a tooling bug).

Input contract (stdin JSON from Claude Code harness):
    { "stop_hook_active": bool, "session_id": "...", ... }
"""
import json
import os
import subprocess
import sys

RATCHET_TIMEOUT_SEC = 60


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("stop_hook_active"):
        return 0

    if os.environ.get("SKIP_DEADCODE") == "1":
        return 0

    # Skip if the working tree has no relevant changes — avoids a ~5s
    # knip run on turns where Claude only answered a question.
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        changed_lines = (r.stdout or "").splitlines()
    except Exception:
        return 0

    code_exts = (".ts", ".tsx", ".js", ".cjs", ".mjs", ".json")
    has_code_changes = any(
        line[3:].strip().strip('"').endswith(code_exts)
        for line in changed_lines
        if len(line) > 3
    )
    if not has_code_changes:
        return 0

    # Run the ratchet. Never block on tooling failures — only on real
    # regressions.
    try:
        result = subprocess.run(
            ["node", "scripts/check-dead-code-baseline.js"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=RATCHET_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        sys.stderr.write(
            "[dead-code-guard] knip exceeded " + str(RATCHET_TIMEOUT_SEC) +
            "s -- skipping check (not blocking).\n"
        )
        return 0
    except FileNotFoundError:
        return 0

    if result.returncode == 0:
        return 0

    # Exit code 1 = genuine regression. Exit code 2 = tooling error (e.g.
    # knip not installed, baseline missing). Only block on genuine
    # regressions.
    if result.returncode != 1:
        return 0

    sys.stderr.write("[dead-code-guard] blocking stop -- dead-code ratchet regressed:\n\n")
    sys.stderr.write(result.stderr or result.stdout or "")
    sys.stderr.write("\n")
    sys.stderr.write("Before finishing, either:\n")
    sys.stderr.write("  - delete the orphan exports/files/deps listed above, OR\n")
    sys.stderr.write("  - wire them to a real consumer if they are intentional, OR\n")
    sys.stderr.write("  - regenerate baseline with `npm run dead-code-baseline` if you\n")
    sys.stderr.write("    cleaned up OTHER files and the floor genuinely dropped.\n")
    sys.stderr.write("\n")
    sys.stderr.write("Bypass for this turn: SKIP_DEADCODE=1 in the env.\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
