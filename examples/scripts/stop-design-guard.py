#!/usr/bin/env python
"""Stop hook: runs the design-contract ratchet before Claude terminates a turn.

If the ratchet fails (new box-shadow / arbitrary border-radius / gradient-text
introduced in a product-register .tsx), exits 2 with stderr so Claude sees the
regression and is forced to clean up before really finishing. Mirrors the
philosophy of the dead-code and any ratchets: the baseline is the floor, the
count can only go down.

Only the three DETERMINISTIC non-negotiables from DESIGN.md are enforced here.
The accent-≤8% rule is not statically distinguishable from a legitimate yellow
button fill, so it lives in the on-demand visual audit (/design-gate → impeccable).

Skip conditions (all exit 0, no-op):
  - `stop_hook_active=True` in payload (re-trigger from our own prior block).
  - env `SKIP_DESIGN=1` (explicit bypass).
  - no .tsx changes in the working tree (the gate only scans .tsx).
  - baseline missing (`.design-baseline.json`) — gate not initialized yet.
  - the check script itself crashes or times out (never block on a tooling bug).

Input contract (stdin JSON from Claude Code harness):
    { "stop_hook_active": bool, "session_id": "...", ... }
"""
import json
import os
import subprocess
import sys

RATCHET_TIMEOUT_SEC = 60


def main():
    # Anchor to project root regardless of CWD (hooks inherit whatever cwd the
    # Bash tool left behind, which may be a subdirectory).
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("stop_hook_active"):
        return 0

    if os.environ.get("SKIP_DESIGN") == "1":
        return 0

    # Skip if the working tree has no .tsx changes — the design gate only
    # scans .tsx, so nothing else can move the count.
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

    has_tsx_changes = any(
        line[3:].strip().strip('"').endswith(".tsx")
        for line in changed_lines
        if len(line) > 3
    )
    if not has_tsx_changes:
        return 0

    # Run the ratchet. Never block on tooling failures — only on real
    # regressions.
    try:
        result = subprocess.run(
            ["node", "scripts/check-design-baseline.js"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=RATCHET_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        sys.stderr.write(
            "[design-guard] check exceeded " + str(RATCHET_TIMEOUT_SEC) +
            "s -- skipping (not blocking).\n"
        )
        return 0
    except FileNotFoundError:
        return 0

    if result.returncode == 0:
        return 0

    # Exit code 1 = genuine regression. Exit code 2 = tooling error (e.g.
    # baseline missing). Only block on genuine regressions.
    if result.returncode != 1:
        return 0

    sys.stderr.write("[design-guard] blocking stop -- design-contract ratchet regressed:\n\n")
    sys.stderr.write(result.stderr or result.stdout or "")
    sys.stderr.write("\n")
    sys.stderr.write("Before finishing, on the product/panel surface either:\n")
    sys.stderr.write("  - replace box-shadow with the tonal ramp + a 1px argent border (shadow-none), OR\n")
    sys.stderr.write("  - drop the arbitrary rounded-[...] (named rounded-* render square; the spinner is exempt), OR\n")
    sys.stderr.write("  - remove the gradient-text (emphasis is weight/size/classic color), OR\n")
    sys.stderr.write("  - if the surface is `brand` register (public report / /tools/* / portal), move it under\n")
    sys.stderr.write("    one of the exempt paths, OR\n")
    sys.stderr.write("  - if you cleaned up OTHER files and the floor genuinely dropped, run\n")
    sys.stderr.write("    `npm run design-baseline`.\n")
    sys.stderr.write("\n")
    sys.stderr.write("Bypass for this turn: SKIP_DESIGN=1 in the env.\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
