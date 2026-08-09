#!/usr/bin/env python3
"""Nudge minimo de graphify para PreToolUse (Bash / Read / Glob).

Reemplaza a `python -m graphify hook-guard {search,read}`, que inyectaba
200-490 chars en CADA tool call. Como PreToolUse inyecta al final del array
de mensajes, ese texto se ACUMULA en el historial y se re-paga en cada turno
siguiente (costo cuadratico). El detalle de las reglas de graphify ya vive en
CLAUDE.md, que se cachea y se paga una vez a 0.1x -- aca solo queda el
recordatorio corto.

Silencioso si no hay grafo: sin graphify-out/graph.json no hay nada que empujar.
"""
import json
import os
import sys

NUDGE = 'graphify query "<pregunta>" antes de grepear/leer codigo (ver CLAUDE.md).'


def main() -> int:
    try:
        sys.stdin.read()  # drenar el payload; no lo necesitamos
    except Exception:
        pass

    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    if not os.path.isfile(os.path.join(root, "graphify-out", "graph.json")):
        return 0  # sin grafo, sin nudge

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": NUDGE,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
