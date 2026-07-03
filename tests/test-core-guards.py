#!/usr/bin/env python3
"""Smoke tests for the core hook guards. Run from anywhere:

    python tests/test-core-guards.py

Uses examples/worker-brain/ as the stack.json fixture (it configures
environment.forbiddenCommands, gates.push=operator-only and
gates.closeProtocol=blocking). No external deps.
"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(REPO, "core", "hooks", "scripts")
FIXTURE = os.path.join(REPO, "examples", "worker-brain")   # has stack.json
NO_MANIFEST = os.path.dirname(REPO)                         # parent dir: no stack.json upward (best effort)

ENV = {k: v for k, v in os.environ.items()
       if k not in ("SKIP_CANONICAL", "ALLOW_CLAUDE_PUSH", "SKIP_PREPUSH", "SKIP_COMMITCHECK")}


def run(script, payload, cwd):
    return subprocess.run(
        [sys.executable, os.path.join(CORE, script)],
        input=json.dumps(payload), capture_output=True, text=True, env=ENV, cwd=cwd,
    )


def main():
    cases = [
        # canonical-guard: config-driven forbidden commands
        ("canonical-guard.py", {"tool_input": {"command": "npx eslint src/"}}, FIXTURE, 2),
        ("canonical-guard.py", {"tool_input": {"command": "npm run lint"}}, FIXTURE, 0),
        ("canonical-guard.py", {"tool_input": {"command": "cat x | jq ."}}, FIXTURE, 2),
        ("canonical-guard.py", {"tool_input": {"command": "SKIP_CANONICAL=1 npx eslint src/"}}, FIXTURE, 0),
        # push policy: operator-only intercepts everything except --dry-run
        ("pre-push-guard.py", {"tool_input": {"command": "git push origin main"}}, FIXTURE, 2),
        ("pre-push-guard.py", {"tool_input": {"command": "git push --no-verify"}}, FIXTURE, 2),
        ("pre-push-guard.py", {"tool_input": {"command": "git push --dry-run"}}, FIXTURE, 0),
        ("pre-push-guard.py", {"tool_input": {"command": "git commit -m x"}}, FIXTURE, 0),
        # close-guard: stop_hook_active always exits 0 (anti-loop)
        ("close-guard.py", {"stop_hook_active": True}, FIXTURE, 0),
        # malformed stdin never blocks
        ("canonical-guard.py", None, FIXTURE, 0),
    ]

    fails = 0
    for script, payload, cwd, expected in cases:
        if payload is None:
            r = subprocess.run([sys.executable, os.path.join(CORE, script)],
                               input="not-json", capture_output=True, text=True, env=ENV, cwd=cwd)
        else:
            r = run(script, payload, cwd)
        ok = r.returncode == expected
        if not ok:
            fails += 1
        label = payload.get("tool_input", {}).get("command", "-")[:40] if isinstance(payload, dict) else "malformed stdin"
        print(("OK  " if ok else "FAIL") + f" {script} [{label}] exit={r.returncode} expected={expected}")

    print(("PASS" if fails == 0 else "FAIL") + f" — {len(cases) - fails}/{len(cases)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
