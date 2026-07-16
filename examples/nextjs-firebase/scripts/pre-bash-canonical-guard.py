#!/usr/bin/env python
"""PreToolUse hook (Bash): blocks commands that ALWAYS fail on this machine.

Each pattern below burned 1-3 turns per session across 19 sessions
(friction audit 2026-07): the agent picks the "default" path when this
environment only supports the canonical one. Blocking with the exact
correction in the message turns the gotcha into a 0-turn self-fix.

The full canonical-vs-forbidden table lives in
.claude/rules/windows-environment.md.

Bypass: SKIP_CANONICAL=1 in the env.

Input contract (stdin JSON from Claude Code harness):
    { "tool_input": { "command": "..." }, ... }

NOTE: keep every message ASCII-only — cp1252 consoles mangle accents.
"""
import json
import os
import re
import sys

# (pattern, correction) — first match wins. Patterns are checked against
# the raw Bash command string.
RULES = [
    (
        r"(^|[;&|]\s*)(npx\s+)?eslint\b",
        "eslint directo falla aca (ESLint 9 global sin eslint.config)."
        " Usa: npm run lint  |  fix: npx next lint --fix",
    ),
    (
        r"\bfirebase\s+(login|deploy|firestore|use)\b",
        "El CLI de firebase pide login interactivo y muere headless."
        " Firestore/indexes: npx tsx --require ./scripts/load-env.cjs"
        " scripts/ops/deploy-firestore-indexes.ts --apply (service account,"
        " nunca vence). Lecturas/escrituras: scripts con load-env.cjs.",
    ),
    (
        r"(^|[;&|(]\s*)jq\b|\|\s*jq\b",
        "jq no esta instalado en esta maquina."
        " Usa: node -e \"const d=JSON.parse(require('fs').readFileSync(0,'utf8')); ...\"",
    ),
    (
        r"\b(Select-Object|ForEach-Object|Get-ChildItem|Get-Content|Write-Host|Select-String|Test-Path)\b|\$env:",
        "Eso es sintaxis PowerShell dentro del tool Bash."
        " Usa el tool PowerShell para cmdlets PS, o sintaxis POSIX en Bash.",
    ),
]


def main():
    if os.environ.get("SKIP_CANONICAL") == "1":
        return 0

    try:
        payload = json.loads(sys.stdin.read().lstrip("\ufeff"))
    except Exception:
        return 0

    cmd = (payload.get("tool_input", {}) or {}).get("command", "") or ""
    if not cmd:
        return 0

    # El env prefijado en el comando no llega al proceso del hook \u2014 aceptar el
    # marker dentro del comando mismo: `SKIP_CANONICAL=1 <cmd>`.
    if "SKIP_CANONICAL=1" in cmd:
        return 0

    for pattern, fix in RULES:
        if re.search(pattern, cmd):
            sys.stderr.write("[canonical-guard] comando bloqueado en esta maquina:\n")
            sys.stderr.write("  " + cmd.strip()[:200] + "\n\n")
            sys.stderr.write("  " + fix + "\n\n")
            sys.stderr.write(
                "  Tabla completa: .claude/rules/windows-environment.md"
                "  |  Bypass: SKIP_CANONICAL=1\n"
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
