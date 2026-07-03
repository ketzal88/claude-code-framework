#!/usr/bin/env python
"""Stop hook (close-protocol): avisa UNA vez si el turno cierra con codigo sin commitear.

Friccion que ataca (auditoria 2026-07, 16 sesiones): Claude termina el
trabajo pero no commitea ni reporta estado, y el operador persigue con
"comiteaste?". El cierre correcto de trabajo sustancial es: correr la
secuencia de /commit-checkpoint, commitear, y terminar el mensaje con
"commiteado: <sha corto> - N commit(s) listos para push".

Bloquea con exit 2 SOLO una vez por cierre (stop_hook_active corta el
loop). Si los cambios son WIP deliberado o deuda heredada de otra sesion,
Claude lo dice en el mensaje final y cierra igual en el retry.

Skip conditions (exit 0):
  - stop_hook_active=True (re-trigger de nuestro propio bloqueo previo).
  - SKIP_COMMITCHECK=1 (bypass explicito).
  - working tree limpio, o solo cambios docs/config (.md, docs/, .claude/).

NOTE: mensajes ASCII-only (consolas cp1252).
"""
import json
import os
import subprocess
import sys

DOC_ONLY_HINTS = (".md",)
DOC_DIR_PREFIXES = ("docs/", ".claude/", ".github/")


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    try:
        payload = json.loads(sys.stdin.read().lstrip("\ufeff"))
    except Exception:
        return 0

    if payload.get("stop_hook_active"):
        return 0

    if os.environ.get("SKIP_COMMITCHECK") == "1":
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
        changed_lines = [ln for ln in (r.stdout or "").splitlines() if len(ln) > 3]
    except Exception:
        return 0

    code_files = []
    for line in changed_lines:
        path = line[3:].strip().strip('"').replace("\\", "/")
        if path.endswith(DOC_ONLY_HINTS):
            continue
        if any(path.startswith(p) for p in DOC_DIR_PREFIXES):
            continue
        code_files.append(path)

    if not code_files:
        return 0

    sys.stderr.write(
        "[close-protocol] quedan " + str(len(code_files)) +
        " archivo(s) de codigo sin commitear:\n"
    )
    for p in code_files[:10]:
        sys.stderr.write("  " + p + "\n")
    if len(code_files) > 10:
        sys.stderr.write("  ... y " + str(len(code_files) - 10) + " mas\n")
    sys.stderr.write(
        "\nAntes de cerrar, elegi UNA:\n"
        "  a) Es trabajo tuyo terminado -> corre la secuencia de /commit-checkpoint,\n"
        "     commitea, y termina el mensaje con 'commiteado: <sha> - N commit(s)\n"
        "     listos para push'. NUNCA hagas git push (es de el operador).\n"
        "  b) Es WIP deliberado o deuda de OTRA sesion -> decilo explicitamente en\n"
        "     tu mensaje final (que archivos y por que quedan sin commitear) y cerra.\n"
        "\nEste aviso aparece una sola vez por cierre. Bypass: SKIP_COMMITCHECK=1.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
