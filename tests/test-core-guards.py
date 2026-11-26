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

        # 1.5.0: the commit is found anywhere in the command, not only at its start
        checks.append(("compound: status && commit", guard("git status && git commit -m x").returncode, 2))
        checks.append(("git -C <dir> commit", guard(f'git -C "{tmp}" commit -m x').returncode, 2))
        checks.append(("cd <dir> && commit", guard(f'cd "{tmp}" && git commit -m x').returncode, 2))
        subprocess.run(["git", "rm", "-q", "--cached", ".env"], cwd=tmp, env=env)
        os.remove(os.path.join(tmp, ".env"))
        checks.append(("clean again", guard("git commit -m x").returncode, 0))

        # pending mode: `git add -A && git commit` scans what the add is about to stage
        key = "AKIA" + "ABCDEFGHIJKLMNOP"  # split so this file never matches itself
        with open(os.path.join(tmp, "cfg.txt"), "w") as fh:
            fh.write("aws = " + key + "\n")
        checks.append(("add -A && commit, untracked key", guard("git add -A && git commit -m x").returncode, 2))
        checks.append(("plain commit, key not staged", guard("git commit -m x").returncode, 0))
        # 1.5.1: parser tricks that used to fall back to a staged-only scan
        checks.append(("-a after -m value", guard("git commit -m x -a").returncode, 2))
        checks.append(("pathspec after -m", guard("git commit -m x cfg.txt").returncode, 2))
        os.makedirs(os.path.join(tmp, "sub"), exist_ok=True)
        checks.append(("add in subdir, commit at root",
                       guard("git -C sub add -A && git commit -m x").returncode, 2))
        checks.append(("bash -c wrapper", guard('bash -c "git add -A && git commit -m x"').returncode, 2))
        checks.append(("subshell", guard("(git add -A && git commit -m x)").returncode, 2))
        checks.append(("env prefix", guard("env GIT_X=1 git commit -am x").returncode, 2))
        checks.append(("dir created in same command",
                       guard("mkdir nd && cd nd && git commit -m x").returncode, 2))
        # 1.5.2: parser differentials found by review
        checks.append(("brace inside -m value", guard("git commit -m{x} -a").returncode, 2))
        checks.append(("--pathspec-from-file", guard("git commit -m x --pathspec-from-file=l").returncode, 2))
        checks.append(("unknown long option", guard("git commit -m x --future-flag").returncode, 2))
        checks.append(("sudo -u <value>", guard("sudo -u git git commit -am x").returncode, 2))
        checks.append(("bash -o <value> -c", guard('bash -o pipefail -c "git commit -am x"').returncode, 2))
        checks.append(("eval string", guard('eval "git commit -am x"').returncode, 2))
        checks.append(("env -S string", guard('env -S "git commit -am x"').returncode, 2))
        deep = 'bash -c "bash -c \\"bash -c \\\\\\"bash -c git\\\\\\" commit\\""'
        checks.append(("nested too deep fails closed", guard(deep).returncode, 2))
        checks.append(("safe flags stay staged-only", guard("git commit -qm x --no-verify").returncode, 0))
        os.remove(os.path.join(tmp, "cfg.txt"))
        with open(os.path.join(tmp, "big.txt"), "w") as fh:
            fh.write(("x" * 100 + "\n") * 12000 + "aws = " + key + "\n")
        checks.append(("untracked file over 1 MB", guard("git add -A && git commit -m x").returncode, 2))
        os.remove(os.path.join(tmp, "big.txt"))
        with open(os.path.join(tmp, "cfg.txt"), "w") as fh:
            fh.write("aws = " + key + "\n")

        # a commit that DELETES a secret is not blocked (only added lines count)
        subprocess.run(["git", "add", "cfg.txt"], cwd=tmp, env=env)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "seed",
                        "--no-verify"], cwd=tmp, env=env)
        os.remove(os.path.join(tmp, "cfg.txt"))
        checks.append(("deleting a secret", guard("git add -A && git commit -m x").returncode, 0))

        # templates with variable names only are allowed
        with open(os.path.join(tmp, ".env.example"), "w") as fh:
            fh.write("API_URL=\n")
        checks.append((".env.example allowed", guard("git add -A && git commit -m x").returncode, 0))

        # explicit allow marker on the line
        with open(os.path.join(tmp, "fixture.txt"), "w") as fh:
            fh.write("sample = " + key + "  # secret-scan:allow test fixture\n")
        checks.append(("secret-scan:allow", guard("git add -A && git commit -m x").returncode, 0))

        for label, got, expected in checks:
            total += 1
            ok = got == expected
            fails += 0 if ok else 1
            print(("OK  " if ok else "FAIL")
                  + f" secret-scan-guard.py [{label}] exit={got} expected={expected}")
    return fails, total


def config_cases():
    """Gates that need their own stack.json: pushWrappers, canonical `unless`,
    and the session-scoped close-guard. Returns (fails, total)."""
    import tempfile
    fails, total = 0, 0
    with tempfile.TemporaryDirectory() as tmp:
        stack = {
            "gates": {"push": "operator-only", "closeProtocol": "blocking",
                      "pushWrappers": ["(^|[;&|]\\s*)npm run release\\b"]},
            "environment": {"forbiddenCommands": [
                {"pattern": "(^|[;&|]\\s*)foo\\s+login\\b", "unless": "--token",
                 "fix": "Use foo login --token"}]},
        }
        with open(os.path.join(tmp, "stack.json"), "w") as fh:
            json.dump(stack, fh)
        subprocess.run(["git", "init", "-q"], cwd=tmp, env=ENV)
        inner = os.path.join(tmp, "inner")
        os.makedirs(inner)
        subprocess.run(["git", "init", "-q"], cwd=inner, env=ENV)
        with open(os.path.join(inner, "stack.json"), "w") as fh:
            json.dump({"gates": {}}, fh)  # no push policy in the nested repo
        env = dict(ENV, CLAUDE_PROJECT_DIR=tmp)

        def hook(script, payload):
            return subprocess.run(
                [sys.executable, os.path.join(CORE, script)], input=json.dumps(payload),
                capture_output=True, text=True, env=env, cwd=tmp,
            ).returncode

        def bash(cmd):
            return {"tool_input": {"command": cmd}}

        checks = [
            ("pre-push: push inside a compound", hook("pre-push-guard.py", bash("npm test && git push")), 2),
            ("pre-push: -o value is not --dry-run", hook("pre-push-guard.py", bash("git push -o -n origin main")), 2),
            ("pre-push: real -n is a dry run", hook("pre-push-guard.py", bash("git push -n origin main")), 0),
            ("pre-push: env wrapper", hook("pre-push-guard.py", bash("env git push")), 2),
            ("pre-push: nested repo uses its own stack.json",
             hook("pre-push-guard.py", bash("git -C inner push")), 0),
            ("pre-push: bash -c too deep fails closed",
             hook("pre-push-guard.py", bash('bash -c "bash -c \\"bash -c \\\\\\"bash -c git push\\\\\\"\\""')), 2),
            ("pre-push: pushWrapper",hook("pre-push-guard.py", bash("npm run release")), 2),
            ("pre-push: unrelated npm script", hook("pre-push-guard.py", bash("npm run build")), 0),
            ("canonical: pattern fires", hook("canonical-guard.py", bash("foo login")), 2),
            ("canonical: unless suppresses", hook("canonical-guard.py", bash("foo login --token $T")), 0),
            ("canonical: anchored, no false hit", hook("canonical-guard.py", bash("npm view foo login")), 0),
        ]

        # close-guard, session-scoped: two dirty code files, only one touched by this session
        for name in ("mine.ts", "theirs.ts"):
            with open(os.path.join(tmp, name), "w") as fh:
                fh.write("export const x = 1\n")
        transcript = os.path.join(tmp, "transcript.jsonl")

        def write_transcript(paths):
            with open(transcript, "w") as fh:
                fh.write(json.dumps({"type": "user", "timestamp": "2026-01-01T00:00:00Z"}) + "\n")
                for p in paths:
                    fh.write(json.dumps({"message": {"content": [{
                        "type": "tool_use", "name": "Write",
                        "input": {"file_path": os.path.join(tmp, p)}}]}}) + "\n")

        stop = {"transcript_path": transcript, "cwd": tmp}
        write_transcript(["mine.ts"])
        checks.append(("close: own dirty file blocks", hook("close-guard.py", stop), 2))
        write_transcript([])
        checks.append(("close: only foreign dirty files", hook("close-guard.py", stop), 0))
        checks.append(("close: unreadable transcript -> 1.4 behaviour",
                       hook("close-guard.py", {"transcript_path": os.path.join(tmp, "nope.jsonl"),
                                               "cwd": tmp}), 2))

        for label, got, expected in checks:
            total += 1
            ok = got == expected
            fails += 0 if ok else 1
            print(("OK  " if ok else "FAIL") + f" [{label}] exit={got} expected={expected}")
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
    c_fails, c_total = config_cases()
    fails += c_fails
    total = len(cases) + s_total + g_total + c_total
    print(("PASS" if fails == 0 else "FAIL") + f" — {total - fails}/{total}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
