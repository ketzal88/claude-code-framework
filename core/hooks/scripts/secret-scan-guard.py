"""PreToolUse(Bash) guard: run secret-scan.sh before ANY git commit in the command.

EXIT-CODE CONTRACT: Claude Code blocks a tool ONLY on exit 2. Exit 1 is a
non-blocking error and the tool runs anyway. secret-scan.sh exits 1 on a hit,
so this wrapper maps any non-zero scanner exit to 2. (A wrapper that propagated
the 1 blocked nothing for months; tests pin the mapping.)

DETECTION (1.5.0): the commit is found in any segment of the command, with
`cd X &&` and `git -C X` applied (see git_target.py). Until 1.4 only commands
that STARTED with `git commit` were scanned, and `git add -A && git commit`
let a token through to a shared repo.

PENDING MODE: in `git add ... && git commit` (or `git commit -a`) nothing is
staged yet when this hook runs, because the add has not executed. In that case
the scanner runs with SECRET_SCAN_MODE=pending and also inspects unstaged and
untracked files, which is what the add is about to stage.

Missing scanner = setup error, not a secret: the commit is allowed with a loud
message instead of blocking every commit forever.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import git_target  # noqa: E402

BLOCK = 2  # Claude Code: exit 2 = deny the tool and show stderr to the model
ALLOW = 0


def commit_stages_more(args):
    """True if `git commit` itself stages files (-a, --all, -am, ...)."""
    for a in args:
        if a == "--all":
            return True
        if a.startswith("-") and not a.startswith("--") and "a" in a[1:]:
            # short-flag cluster such as -am; stop at -m's value (next word)
            return True
        if a in ("-m", "-F", "--message", "--file"):
            break
    return False


def main():
    try:
        payload = json.loads(sys.stdin.read().lstrip("\ufeff"))
    except Exception:
        sys.exit(ALLOW)  # unreadable payload: we cannot tell if it is a commit
    if not isinstance(payload, dict):
        sys.exit(ALLOW)
    cmd = ((payload.get("tool_input") or {}).get("command") or "")
    if "commit" not in cmd:
        sys.exit(ALLOW)

    calls = list(git_target.git_calls(cmd, git_target.base_dir(payload)))
    targets = {}  # directory -> mode
    added_dirs = set()
    for sub, args, directory in calls:
        if sub == "add":
            added_dirs.add(directory)
        elif sub == "commit":
            pending = directory in added_dirs or commit_stages_more(args)
            if pending or directory not in targets:
                targets[directory] = "pending" if pending else "staged"
    if not targets:
        sys.exit(ALLOW)

    # Resolve the scanner next to THIS file: core/ can live anywhere, and a wrong
    # guess makes bash fail, which would map to BLOCK and deny every commit.
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secret-scan.sh")
    if not os.path.isfile(script):
        print(
            f"secret-scan-guard: scanner not found at {script} - commit ALLOWED "
            f"because this is a setup error, not a detected secret. Fix the install.",
            file=sys.stderr,
        )
        sys.exit(ALLOW)

    for directory, mode in targets.items():
        if not os.path.isdir(directory):
            continue  # cd into a dir that does not exist: git will fail on its own
        env = dict(os.environ, SECRET_SCAN_MODE=mode)
        rc = subprocess.call(["bash", script], cwd=directory, env=env)
        if rc != 0:
            print(f"secret-scan-guard: commit in {directory} blocked ({mode} scan).",
                  file=sys.stderr)
            sys.exit(BLOCK)
    sys.exit(ALLOW)


if __name__ == "__main__":
    main()
