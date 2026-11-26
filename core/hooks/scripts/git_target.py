#!/usr/bin/env python3
"""git_target: find every git invocation inside a Bash command, and where it runs.

Shared helper for the PreToolUse guards (secret-scan-guard, pre-push-guard).
Not a hook by itself.

Why it exists: guards that only looked at `cmd.startswith("git commit")` were
bypassed by ordinary agent habits, and a token reached a shared repo that way:

    cd sub && git commit -m x          (leading cd)
    git add -A && git commit -m x      (commit is the second segment)
    git -C ../other commit -m x        (global option before the subcommand)
    FOO=1 git push                     (env assignment prefix)

So the command is split into segments on && || ; | and newlines (outside
quotes), each segment is parsed with shlex, a `cd X` segment moves the working
directory for the segments after it, and `git -C X` moves it for that one call.

On Windows, MSYS paths (/c/Users/...) are converted to C:/Users/... so the
directory can be handed to subprocess.

ASCII-only on purpose: hook consoles on Windows are often cp1252.
"""
import os
import re
import shlex

# Global git options that consume the next argument (`git -C dir`, `git -c k=v`).
OPTS_WITH_VALUE = {"-C", "-c", "--exec-path", "--namespace", "--git-dir", "--work-tree"}
ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
MSYS_DRIVE = re.compile(r"^/([a-zA-Z])(/|$)")


def normalize(path):
    """MSYS /c/foo -> C:/foo on Windows; anything else unchanged."""
    if os.name == "nt":
        m = MSYS_DRIVE.match(path)
        if m:
            return m.group(1).upper() + ":/" + path[len(m.group(0)):]
    return path


def base_dir(payload):
    """Directory the Bash tool runs in: payload cwd, then CLAUDE_PROJECT_DIR, then ours."""
    cwd = (payload or {}).get("cwd") if isinstance(payload, dict) else None
    return cwd or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def segments(cmd):
    """Split a shell command on && || ; | & and newlines, respecting quotes.

    Deliberately simple: no subshells or heredoc parsing. Good enough to find
    a `git` word at command position, which is all the guards need.
    """
    out, buf, quote, i = [], [], None, 0
    while i < len(cmd):
        ch = cmd[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < len(cmd):
                buf.append(cmd[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch in ";\n|&":
            out.append("".join(buf))
            buf = []
            # swallow the second char of && and ||
            if ch in "|&" and i + 1 < len(cmd) and cmd[i + 1] == ch:
                i += 1
            i += 1
            continue
        buf.append(ch)
        i += 1
    out.append("".join(buf))
    return [s.strip() for s in out if s.strip()]


def _words(segment):
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def _resolve(cur, target):
    target = normalize(target)
    if target in ("~", "") or target.startswith("~/"):
        target = os.path.expanduser(target)
    return target if os.path.isabs(target) else os.path.normpath(os.path.join(cur, target))


def git_calls(cmd, start_dir):
    """Yield (subcommand, args, directory) for each git invocation in cmd.

    `directory` is where that git call operates (cd and -C applied).
    `args` are the words after the subcommand.
    """
    cur = normalize(start_dir)
    for seg in segments(cmd):
        words = _words(seg)
        # strip leading env assignments (FOO=1 git push)
        while words and ENV_ASSIGN.match(words[0]):
            words = words[1:]
        if not words:
            continue
        if words[0] == "cd":
            if len(words) > 1:
                cur = _resolve(cur, words[1])
            continue
        if os.path.basename(words[0]).lower() not in ("git", "git.exe"):
            continue
        here = cur
        i = 1
        sub = None
        while i < len(words):
            w = words[i]
            if w in OPTS_WITH_VALUE:
                if w == "-C" and i + 1 < len(words):
                    here = _resolve(here, words[i + 1])
                i += 2
                continue
            if w.startswith("-"):
                i += 1
                continue
            sub = w
            break
        if sub:
            yield sub, words[i + 1:], here


def find(cmd, start_dir, subcommand):
    """All (args, directory) for one subcommand, e.g. find(cmd, d, "commit")."""
    return [(a, d) for s, a, d in git_calls(cmd, start_dir) if s == subcommand]
