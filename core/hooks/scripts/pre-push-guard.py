#!/usr/bin/env python3
"""PreToolUse hook: blocks `git push` until manifest gates pass.

Reads gates.prePush.steps from stack.json. For each step, resolves the
command from commands.<step> or ratchets.<step>. Absent key = step skipped.

All steps run regardless of individual failures (mirrors CI if:always()).

SKIP_PREPUSH=1 allowed only when ALL changed files match CI_PATHS_IGNORE.

1.5.0 - DETECTION: the push is found in any segment of the command
(`cd x && git push`, `git -C x push`, `npm test && git push`), not only when
the command starts with `git push`; the checks run in the directory the push
targets. gates.pushWrappers (array of regexes) names project scripts that push
on your behalf (e.g. "npm run (ship|release)"): they are treated as a push,
so the operator-only policy cannot be dodged by calling the wrapper.

Input contract (stdin JSON from Claude Code harness):
    { "tool_input": { "command": "git push ..." }, ... }
"""
import json
import os
import re
import subprocess
import sys
import time

TIMEOUT_SEC = int(os.environ.get("PREPUSH_TIMEOUT", "300"))
TAIL_LINES = 40
CI_PATHS_IGNORE = [
    r"\.md$",
    r"^\.claude/",
    r"^docs/",
    r"^\.gitignore$",
    r"^\.gitattributes$",
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
READ_CONFIG = os.path.join(SCRIPT_DIR, "read-config.py")
sys.path.insert(0, SCRIPT_DIR)
import git_target  # noqa: E402


def cfg(key):
    """Read a dotted key from stack.json via read-config.py."""
    try:
        r = subprocess.run(
            [sys.executable, READ_CONFIG, key],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def changed_files(cwd=None):
    for args in [
        ["git", "diff", "--name-only", "origin/main...HEAD"],
        ["git", "diff", "--name-only", "HEAD~1"],
    ]:
        try:
            r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip().splitlines()
        except Exception:
            pass
    return []


def all_docs_only(files):
    if not files:
        return False
    return all(any(re.search(p, f) for p in CI_PATHS_IGNORE) for f in files)


def tail(text, n):
    lines = text.splitlines()
    return lines[-n:] if len(lines) > n else lines


# `git push` options that take the next word as their value.
PUSH_OPTS_WITH_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}


def is_dry_run(args):
    """True only for a real -n/--dry-run flag, not a word that is an option value."""
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            return False
        if a in PUSH_OPTS_WITH_VALUE:
            i += 2
            continue
        if a == "--dry-run":
            return True
        if a.startswith("-") and not a.startswith("--") and len(a) > 1:
            flags = a[1:]
            for ch in flags:
                if ch == "n":
                    return True
                if ch == "o":
                    break  # -oVALUE: the rest is the value
        i += 1
    return False


def main():
    try:
        payload = json.loads(sys.stdin.read().lstrip("\ufeff"))
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    push_cmd = (payload.get("tool_input", {}) or {}).get("command", "") or ""
    if not push_cmd:
        return 0

    pushes = git_target.find(push_cmd, git_target.base_dir(payload), "push")
    real = [(a, d) for a, d in pushes if not is_dry_run(a)]
    wrapper = None
    wrappers_raw = None if real else cfg("gates.pushWrappers")
    if wrappers_raw:
        try:
            wrappers = json.loads(wrappers_raw)
        except Exception:
            wrappers = []
        for rx in wrappers if isinstance(wrappers, list) else []:
            try:
                if re.search(rx, push_cmd):
                    wrapper = rx
                    break
            except re.error:
                continue  # malformed pattern in config: never block on config bugs
    if not real and not wrapper:
        return 0
    target_dir = real[0][1] if real else git_target.base_dir(payload)
    if not os.path.isdir(target_dir):
        target_dir = None

    # -- Push policy (close-protocol) -------------------------------------
    # gates.push = "operator-only" in stack.json => the agent NEVER pushes:
    # every `git push` (including --no-verify - that was the bypass agents
    # kept trying) blocks instantly with the correct close instruction,
    # BEFORE burning minutes of checks on a push the operator will do by
    # hand anyway. Explicit exception: ALLOW_CLAUDE_PUSH=1 (operator asked
    # in chat) -> the full check suite below runs before allowing it.
    if cfg("gates.push") == "operator-only":
        allow = os.environ.get("ALLOW_CLAUDE_PUSH") == "1" or "ALLOW_CLAUDE_PUSH=1" in push_cmd
        if not allow:
            sys.stderr.write(
                "[close-protocol] git push blocked: pushing belongs to the operator.\n"
                "  Do not retry or use bypasses (--no-verify / SKIP_PREPUSH).\n"
                "  Correct close: commit locally and end your message with\n"
                "  'committed: <short sha> - N commit(s) ready to push'.\n"
                "  If the operator explicitly asked you to push: ALLOW_CLAUDE_PUSH=1 git push ...\n"
            )
            return 2

    if "--no-verify" in push_cmd or (wrapper and not real):
        return 0  # a wrapper runs its own checks; the policy above is what matters

    if os.environ.get("SKIP_PREPUSH") == "1":
        files = changed_files(target_dir)
        if all_docs_only(files):
            return 0
        sys.stderr.write(
            "[pre-push] SKIP_PREPUSH=1 rejected: changed files include code.\n"
            "  Only allowed when ALL changes are docs/config (CI paths-ignore).\n"
        )
        return 2

    # Resolve steps from manifest
    steps_raw = cfg("gates.prePush.steps")
    if not steps_raw:
        return 0  # no manifest or no steps configured

    try:
        steps = json.loads(steps_raw)
        if not isinstance(steps, list):
            steps = [str(steps)]
    except Exception:
        steps = [s.strip() for s in steps_raw.split(",") if s.strip()]

    checks = []
    for step in steps:
        cmd_val = cfg(f"commands.{step}") or cfg(f"ratchets.{step}")
        if cmd_val:
            checks.append((step, cmd_val))

    if not checks:
        return 0

    failures = []
    remaining = TIMEOUT_SEC

    for name, check_cmd in checks:
        if remaining <= 2:
            failures.append((name, "skipped (budget exhausted)", ""))
            continue
        start = time.monotonic()
        env = {**os.environ, "NODE_OPTIONS": "--max-old-space-size=6144"}
        try:
            r = subprocess.run(
                ["bash", "-c", check_cmd], cwd=target_dir,
                capture_output=True, text=True,
                encoding="utf-8", errors="replace",
                timeout=remaining, env=env,
            )
        except subprocess.TimeoutExpired:
            failures.append((name, "timed out", ""))
            remaining = 0
            continue
        except FileNotFoundError:
            sys.stderr.write("[pre-push] bash not found - skipping guard.\n")
            return 0
        elapsed = time.monotonic() - start
        remaining = max(0, int(remaining - elapsed))
        if r.returncode != 0:
            out = (r.stdout or "") + ("\n" + r.stderr if r.stderr else "")
            failures.append((name, f"exit {r.returncode}", out))

    if not failures:
        return 0

    sys.stderr.write(f"[pre-push] {len(failures)} check(s) failed - blocking push:\n\n")
    for name, status, output in failures:
        sys.stderr.write(f"--- {name} ({status}) ---\n")
        for ln in tail(output, TAIL_LINES):
            sys.stderr.write(f"  {ln}\n")
        sys.stderr.write("\n")
    sys.stderr.write(
        "Fix the issues above, then push again.\n"
        "Docs-only bypass: SKIP_PREPUSH=1 git push ...\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
