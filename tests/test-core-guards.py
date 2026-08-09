#!/usr/bin/env python3
"""Smoke tests for the core hook guards. Run from anywhere:

    python tests/test-core-guards.py

Uses examples/nextjs-firebase/ as the stack.json fixture (it configures
environment.forbiddenCommands, gates.push=operator-only and
gates.closeProtocol=blocking). No external deps.
"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(REPO, "core", "hooks", "scripts")
FIXTURE = os.path.join(REPO, "examples", "nextjs-firebase")   # has stack.json
NO_MANIFEST = os.path.dirname(REPO)                         # parent dir: no stack.json upward (best effort)

ENV = {k: v for k, v in os.environ.items()
       if k not in ("SKIP_CANONICAL", "ALLOW_CLAUDE_PUSH", "SKIP_PREPUSH", "SKIP_COMMITCHECK")}


def run(script, payload, cwd):
    return subprocess.run(
        [sys.executable, os.path.join(CORE, script)],
        input=json.dumps(payload), capture_output=True, text=True, env=ENV, cwd=cwd,
    )


def secret_scan_cases():
    """secret-scan.sh needs a git repo with staged files; build a throwaway one.
    Returns (fails, total). Skips (0, 0) if bash is unavailable."""
    import shutil
    import tempfile
    bash = shutil.which("bash")
    if not bash:
        print("SKIP secret-scan.sh (no bash on PATH)")
        return 0, 0
    scanner_src = os.path.join(CORE, "secret-scan.sh")
    patterns_src = os.path.join(REPO, "core", "security", "secret-patterns.txt")
    fails, total = 0, 0
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "core", "hooks", "scripts"))
        os.makedirs(os.path.join(tmp, "core", "security"))
        shutil.copy(scanner_src, os.path.join(tmp, "core", "hooks", "scripts", "secret-scan.sh"))
        shutil.copy(patterns_src, os.path.join(tmp, "core", "security", "secret-patterns.txt"))
        scanner = os.path.join(tmp, "core", "hooks", "scripts", "secret-scan.sh")
        subprocess.run(["git", "init", "-q"], cwd=tmp, env=ENV)

        def scan():
            return subprocess.run([bash, scanner], cwd=tmp, capture_output=True, text=True, env=ENV)

        # 1) the framework's own scanner infra is exempt from the filename check
        subprocess.run(["git", "add", "core/hooks/scripts/secret-scan.sh"], cwd=tmp, env=ENV)
        r = scan()
        total += 1
        ok = r.returncode == 0
        fails += 0 if ok else 1
        print(("OK  " if ok else "FAIL") + f" secret-scan.sh [core/ infra exempt] exit={r.returncode} expected=0")

        # 2) a real secrets-looking filename is still blocked
        open(os.path.join(tmp, ".env"), "w").close()
        subprocess.run(["git", "add", "-f", ".env"], cwd=tmp, env=ENV)
        r = scan()
        total += 1
        ok = r.returncode == 1
        fails += 0 if ok else 1
        print(("OK  " if ok else "FAIL") + f" secret-scan.sh [.env blocked] exit={r.returncode} expected=1")
    return fails, total


def secret_scan_guard_cases():
    """The WRAPPER is what actually denies. The scanner exits 1 on a hit, but Claude
    Code only blocks on exit 2 — a wrapper that propagates the 1 blocks nothing (the
    1.3.2 regression). These cases pin the mapping so it cannot come back.
    Returns (fails, total); skips (0, 0) if bash is unavailable."""
    import shutil
    import tempfile
    if not shutil.which("bash"):
        print("SKIP secret-scan-guard.py (no bash on PATH)")
        return 0, 0
    fails, total = 0, 0
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "init", "-q"], cwd=tmp, env=ENV)
        env = dict(ENV, CLAUDE_PROJECT_DIR=tmp)

        def guard(command):
            return subprocess.run(
                [sys.executable, os.path.join(CORE, "secret-scan-guard.py")],
                input=json.dumps({"tool_input": {"command": command}}),
                capture_output=True, text=True, env=env, cwd=tmp,
            )

        checks = []
        # 1) nothing staged: a commit sails through
        checks.append(("clean tree", guard("git commit -m x").returncode, 0))
        # 2) a staged secret must map the scanner's exit 1 to exit 2 (DENY)
        open(os.path.join(tmp, ".env"), "w").close()
        subprocess.run(["git", "add", "-f", ".env"], cwd=tmp, env=env)
        checks.append(("staged .env -> DENY", guard("git commit -m x").returncode, 2))
        # 3) the guard only cares about commits — everything else is none of its business
        checks.append(("non-commit ignored", guard("git status").returncode, 0))

        for label, got, expected in checks:
            total += 1
            ok = got == expected
            fails += 0 if ok else 1
            print(("OK  " if ok else "FAIL")
                  + f" secret-scan-guard.py [{label}] exit={got} expected={expected}")
    return fails, total


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

    s_fails, s_total = secret_scan_cases()
    fails += s_fails
    g_fails, g_total = secret_scan_guard_cases()
    fails += g_fails
    total = len(cases) + s_total + g_total
    print(("PASS" if fails == 0 else "FAIL") + f" — {total - fails}/{total}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
