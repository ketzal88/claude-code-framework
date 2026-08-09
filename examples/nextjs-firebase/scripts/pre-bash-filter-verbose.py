#!/usr/bin/env python3
"""PreToolUse(Bash): envuelve comandos verbosos conocidos en el filtro de output.

`npm run test:unit` vuelca 370 lineas (~5.900 tok) para decir "45/45 passed";
`test:alerts` vuelca 194 (~3.200 tok). Eso entra al contexto en cada corrida Y
queda en el historial, releido en cada turno posterior. El wrapper muestra el
output completo SOLO si el comando falla.

Medido: test:unit 5.928 -> 34 tok (99.4%), test:alerts 3.219 -> 58 tok (98.2%).

Diseno defensivo -- este hook intercepta TODOS los Bash:
  * Whitelist EXACTA, anclada. Nada de substring matching (el bug que hace
    fallar a CARL: 'spec' matchea dentro de 'especial').
  * No toca comandos que ya traen pipe/redirect/&&: ahi el operador ya decidio
    que quiere ver.
  * Fail-open: ante cualquier duda o excepcion, devuelve {} y el comando corre
    intacto. Un hook de ahorro jamas debe romper un comando.

Doc oficial: code.claude.com/docs/en/costs#offload-processing-to-hooks-and-skills
(el ejemplo de ahi usa jq -- no instalado en esta maquina -- y ademas rompe el
exit code al pipear a grep; ver windows-environment.md).

Bypass: SKIP_OUTPUT_FILTER=1
"""
import json
import os
import re
import sys

WRAPPER = "bash scripts/filter-verbose-output.sh"

# Solo comandos cuyo output es verboso Y cuyo veredicto cabe en una linea.
# tsc/lint quedan afuera a proposito: cuando pasan ya son silenciosos, y cuando
# fallan queremos el error entero.
WRAPPABLE = {
    "npm run test:unit",
    "npm run test:alerts",
    "npm run test:pre-push",
}

# Si el comando ya compone (pipe, redirect, encadenado, subshell), no tocarlo.
COMPOSED = re.compile(r"[|><;&`$]")


def main() -> int:
    if os.environ.get("SKIP_OUTPUT_FILTER") == "1":
        print("{}")
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        print("{}")  # fail-open
        return 0

    try:
        cmd = (payload.get("tool_input") or {}).get("command") or ""
        stripped = cmd.strip()

        if stripped not in WRAPPABLE or COMPOSED.search(stripped):
            print("{}")
            return 0

        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "updatedInput": {"command": WRAPPER + " " + stripped},
            }
        }))
    except Exception:
        print("{}")  # fail-open ante cualquier sorpresa

    return 0


if __name__ == "__main__":
    sys.exit(main())
