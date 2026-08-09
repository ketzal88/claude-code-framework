#!/usr/bin/env python
"""Stop hook: verifies every panel page reaches <AppLayout> before Claude ends a turn.

The failure this exists to stop: this repo has no route-group layout for the
panel, so the chrome (sidebar + header + the max-w-[1400px] work area) comes from
a component each page must remember to wrap itself in. Forgetting it does not
throw and does not warn -- the page just renders full-bleed at viewport width and
"se sale del layout". It shipped on essentially every new section (last:
/anuncios, reported by el operador 2026-07-16).

Only pages this session touched can block (CHANGED_FILES), mirroring the
dead-code/design ratchets: inherited debt from another session downgrades to a
warning, while CI keeps enforcing the global floor.

Skip conditions (all exit 0, no-op):
  - `stop_hook_active=True` in payload (re-trigger from our own prior block).
  - env `SKIP_SHELL=1` (explicit bypass).
  - no `src/app/**/page.tsx` changes in the working tree (nothing can regress).
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

    if os.environ.get("SKIP_SHELL") == "1":
        return 0

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

    changed_paths = [
        line[3:].strip().strip('"').replace("\\", "/")
        for line in changed_lines
        if len(line) > 3
    ]
    # Only a new/edited page.tsx under src/app can move this gate.
    touched_pages = [
        p for p in changed_paths
        if p.startswith("src/app/") and p.endswith("page.tsx")
    ]
    if not touched_pages:
        return 0

    try:
        result = subprocess.run(
            ["node", "scripts/check-page-shell.js"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=RATCHET_TIMEOUT_SEC,
            env={**os.environ, "CHANGED_FILES": "\n".join(touched_pages)},
        )
    except subprocess.TimeoutExpired:
        sys.stderr.write(
            "[shell-guard] check exceeded " + str(RATCHET_TIMEOUT_SEC) +
            "s -- skipping (not blocking).\n"
        )
        return 0
    except FileNotFoundError:
        return 0

    if result.returncode == 0:
        return 0

    # Exit 1 = genuine regression. Anything else = tooling error; never block on it.
    if result.returncode != 1:
        return 0

    sys.stderr.write("[shell-guard] blocking stop -- a panel page has no AppLayout:\n\n")
    sys.stderr.write(result.stderr or result.stdout or "")
    sys.stderr.write("\n")
    sys.stderr.write("This does not throw at runtime -- the page silently renders full-bleed,\n")
    sys.stderr.write("with no sidebar and no padding. Verify in the browser before finishing.\n")
    sys.stderr.write("\n")
    sys.stderr.write("Bypass for this turn: SKIP_SHELL=1 in the env.\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
