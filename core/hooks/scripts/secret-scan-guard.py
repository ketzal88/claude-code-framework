"""PreToolUse(Bash) guard: corre secret-scan.sh SOLO cuando el comando es `git commit`.

CONTRATO DE EXIT CODES — esto era el bug de #1b:
Claude Code bloquea un tool SOLO con `exit 2`. Un `exit 1` lo trata como error
no-bloqueante y el tool se ejecuta igual. `secret-scan.sh` devuelve 1 cuando
detecta un secreto, asi que el wrapper original —que hacia
`sys.exit(subprocess.call(...))`— propagaba ese 1 y por lo tanto NUNCA bloqueaba
un commit. Mapeamos cualquier salida != 0 del scanner a exit 2.

El stderr del scanner (las lineas "BLOCKED: ...") se hereda y llega al modelo.
"""
import json
import os
import subprocess
import sys

BLOCK = 2  # Claude Code: exit 2 = bloquear el tool y mostrar stderr al modelo
ALLOW = 0


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(ALLOW)  # sin payload legible no sabemos si es commit: no bloqueamos
    if not isinstance(payload, dict):
        sys.exit(ALLOW)
    cmd = ((payload.get("tool_input") or {}).get("command") or "")
    if not cmd.lstrip().startswith("git commit"):
        sys.exit(ALLOW)  # solo nos importa `git commit`
    root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or "."
    # Resolve the scanner next to THIS file, not under the project root: core/ can be
    # installed anywhere (.claude/core/, core/, vendored) and a wrong guess here is
    # catastrophic — a missing script makes bash fail, which maps to BLOCK below and
    # would deny every single commit forever.
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secret-scan.sh")
    if not os.path.isfile(script):
        print(
            f"secret-scan-guard: scanner not found at {script} — commit ALLOWED "
            f"because this is a setup error, not a detected secret. Fix the install.",
            file=sys.stderr,
        )
        sys.exit(ALLOW)
    rc = subprocess.call(["bash", script], cwd=root)
    sys.exit(BLOCK if rc != 0 else ALLOW)


if __name__ == "__main__":
    main()
