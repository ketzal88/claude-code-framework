#!/usr/bin/env python
"""Stop hook (ui-smoke-gate): bloquea el cierre si el turno toco UI y no hubo smoke test.

Friccion que ataca (auditoria 2026-07, 20 sesiones — la mas cara): Claude
declara superficies "listas" sin haberlas corrido en browser, y el QA lo
termina haciendo el operador a mano, defecto por defecto. La regla de memoria
(feedback_always_playwright_before_delivery) es prosa; este gate la vuelve
determinista, igual que el dead-code guard.

Logica: si el working tree tiene .tsx modificados bajo src/app/ o
src/components/ (excluyendo /api/) y el transcript de la sesion no
registra NINGUNA llamada a tools de Playwright, exit 2 con la receta
canonica (dev-up + navegacion + screenshot) y el checklist de entrega.

Skip conditions (exit 0):
  - stop_hook_active=True (re-trigger de nuestro propio bloqueo).
  - SKIP_SMOKE=1 (bypass explicito, ej: refactor sin cambio visual).
  - sin .tsx de UI modificados.
  - hubo llamadas Playwright en la sesion (smoke ya corrido).
  - transcript ilegible (nunca bloquear por bug de tooling).

NOTE: mensajes ASCII-only (consolas cp1252).
"""
import json
import os
import subprocess
import sys

PLAYWRIGHT_MARKERS = (
    "mcp__plugin_playwright_playwright__",
    "playwright-cli",
    "npx playwright",
)


def touched_ui_files():
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
        return []
    files = []
    for line in (r.stdout or "").splitlines():
        if len(line) <= 3:
            continue
        path = line[3:].strip().strip('"').replace("\\", "/")
        if not path.endswith(".tsx"):
            continue
        if "/api/" in path:
            continue
        if path.startswith(("src/app/", "src/components/")):
            files.append(path)
    return files


def transcript_has_playwright(transcript_path):
    if not transcript_path or not os.path.isfile(transcript_path):
        return None  # unknown -> never block on tooling gaps
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if any(m in line for m in PLAYWRIGHT_MARKERS):
                    return True
    except Exception:
        return None
    return False


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    try:
        payload = json.loads(sys.stdin.read().lstrip("\ufeff"))
    except Exception:
        return 0

    if payload.get("stop_hook_active"):
        return 0

    if os.environ.get("SKIP_SMOKE") == "1":
        return 0

    ui_files = touched_ui_files()
    if not ui_files:
        return 0

    has_pw = transcript_has_playwright(payload.get("transcript_path"))
    if has_pw is not False:
        return 0  # True (smoke corrido) o None (no se pudo verificar)

    sys.stderr.write(
        "[ui-smoke-gate] tocaste " + str(len(ui_files)) +
        " componente(s) de UI sin correr un smoke test en browser:\n"
    )
    for p in ui_files[:8]:
        sys.stderr.write("  " + p + "\n")
    sys.stderr.write(
        "\nAntes de declarar la UI lista:\n"
        "  1. node scripts/ops/dev-up.mjs   (reusa el dev server vivo o levanta uno)\n"
        "  2. Navega la superficie tocada con Playwright y saca 1 screenshot minimo.\n"
        "     Si tira 'Browser is already in use' -> reintentar con --isolated.\n"
        "  3. Checklist de entrega (.claude/rules/ui-delivery-checklist.md):\n"
        "     - page nueva -> esta cableada en la navegacion?\n"
        "     - componente async -> tiene rama 'sin datos' (no solo skeleton)?\n"
        "     - usa hooks -> 'use client' en linea 1?\n"
        "     - la superficie tiene espejo portal/publico -> se tocaron los dos lados?\n"
        "\nSi el cambio es invisible (refactor puro, tipos): SKIP_SMOKE=1 y decilo en\n"
        "el mensaje final. Este aviso aparece una sola vez por cierre.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
