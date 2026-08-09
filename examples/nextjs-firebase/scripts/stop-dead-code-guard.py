#!/usr/bin/env python
"""Stop hook: runs the dead-code ratchet before Claude terminates a turn.

If the ratchet fails (new orphan exports/files/deps introduced), exits 2
with stderr so Claude sees the regression and is forced to clean up
before really finishing. Mirrors the philosophy of the any-ratchet:
the baseline is the floor, the count can only go down.

Que cuenta como "de esta sesion" lo decide `hook_session_files`, NO
`git status`. La diferencia importa en los dos sentidos:
  - `git status` incluye el WIP de otras sesiones de Claude corriendo sobre
    el mismo repo, y les atribuia esa deuda a esta (falso positivo).
  - `git status` NO incluye lo ya commiteado, asi que commitear alcanzaba
    para escaparle al ratchet entero (falso negativo, el peor de los dos).

Skip conditions (all exit 0, no-op):
  - `stop_hook_active=True` in payload (this is a re-trigger from our own
    prior block — don't loop).
  - env `SKIP_DEADCODE=1` (explicit bypass).
  - esta sesion no toco ningun .ts/.tsx/.js (nada que chequear).
  - knip not installed yet (`.dead-code-baseline.json` missing or knip
    binary absent).
  - knip itself crashes or times out (we never want to block a turn
    because of a tooling bug).

Input contract (stdin JSON from Claude Code harness):
    { "stop_hook_active": bool, "session_id": "...", "transcript_path": "...", ... }
"""
import json
import os
import subprocess
import sys

from hook_session_files import session_touched

RATCHET_TIMEOUT_SEC = 60
CODE_EXTS = (".ts", ".tsx", ".js", ".cjs", ".mjs", ".json")


def working_tree_paths():
    """Fallback: paths sucios del working tree. Set vacio ante error."""
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except Exception:
        return None
    return {
        line[3:].strip().strip('"').replace("\\", "/")
        for line in (r.stdout or "").splitlines()
        if len(line) > 3
    }


def main():
    # Anchor to project root regardless of CWD (hooks inherit whatever cwd
    # the Bash tool left behind, which may be a subdirectory).
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    if payload.get("stop_hook_active"):
        return 0

    if os.environ.get("SKIP_DEADCODE") == "1":
        return 0

    # Lo que toco ESTA sesion: ediciones por tool call + archivos de sus
    # commits. Si el transcript no se puede leer, `session_touched` devuelve
    # None y caemos al working tree (comportamiento viejo): ante la duda,
    # enforzar de mas antes que dejar de enforzar.
    scoped = session_touched(payload.get("transcript_path"), project_root)
    if scoped is None:
        scoped = working_tree_paths()
        if scoped is None:
            return 0

    # Skip si esta sesion no toco codigo — evita ~5s de knip en turnos donde
    # Claude solo respondio una pregunta.
    if not any(p.endswith(CODE_EXTS) for p in scoped):
        return 0

    # Run the ratchet. CHANGED_FILES scopes the block to files THIS session
    # touched — inherited debt from other sessions' WIP downgrades to a
    # warning inside the checker (CI still enforces the global floor).
    # Never block on tooling failures — only on real regressions.
    try:
        result = subprocess.run(
            ["node", "scripts/check-dead-code-baseline.js"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=RATCHET_TIMEOUT_SEC,
            env={**os.environ, "CHANGED_FILES": "\n".join(sorted(scoped))},
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
