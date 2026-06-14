# Adoption Guide

Get the framework running in any repo in ~10 minutes. No language assumptions.

## 1. Copy the core

Copy the universal `core/` into your repo. Two common layouts:

```bash
# Option A — keep it namespaced
cp -r core .claude-framework

# Option B — merge into your existing .claude/
cp -r core/rules    .claude/rules-framework
cp -r core/commands .claude/commands
cp -r core/hooks/scripts scripts/framework
```

Nothing in `core/` references a specific language — it all reads `stack.json` at runtime.

## 2. Write your `stack.json`

Copy the template and fill in the commands your project actually uses:

```bash
cp stack.example.json stack.json
```

Minimum useful manifest (a Python project):

```json
{
  "language": "python",
  "packageManager": "pip",
  "commands": {
    "typecheck": "mypy .",
    "lint": "ruff check",
    "test": "pytest -q"
  },
  "security": {
    "secretScan": "core/hooks/scripts/secret-scan.sh",
    "sast": "bandit -r .",
    "depAudit": "pip-audit"
  },
  "gates": {
    "preCommit": { "secretScan": "blocking" },
    "prePush": { "blocking": true, "steps": ["typecheck", "lint", "test", "sast"] }
  },
  "paths": { "source": ["src/**"], "codeExtensions": [".py"] }
}
```

**Rules of the manifest:**
- Every key is optional. An absent key → that gate is skipped silently (never an error).
- `gates.prePush.steps` are resolved in order from `commands.<step>` first, then `ratchets.<step>`.
- Validate against [`../stack.schema.json`](../stack.schema.json) if your editor supports JSON Schema.

Sanity-check a key:

```bash
python core/hooks/scripts/read-config.py commands.test
# -> pytest -q   (exit 0)     |   empty + exit 1 if the key is absent
```

## 3. Wire the hooks

Merge `core/hooks/settings.template.json` into your `.claude/settings.json`. The important ones:

| Hook | Event | Effect |
|---|---|---|
| secret-scan | `PreToolUse` on `git commit` | **Blocks** the commit if a secret is staged |
| pre-push gate | `PreToolUse` on `git push` | **Blocks** the push if any `gates.prePush.steps` fails |
| ratchet guard | `Stop` | **Blocks** turn end if a ratchet regressed vs its baseline |

> The secret-scan **must** be `PreToolUse`: after a commit completes, `git diff --cached` is empty,
> so a `PostToolUse` hook would never catch anything.

## 4. (Optional) Adopt the ratchets

Ratchets enforce "the baseline is the floor." To turn one on:

```bash
# 1. install the detector for your language (e.g. knip for JS, vulture for Python)
# 2. declare it in stack.json -> ratchets.deadCode
# 3. freeze the initial baseline (commit it)
#    the ratchet blocks any regression above the frozen count
```

The **structural ratchet** (`ratchets.structural`, e.g. `sentrux gate`) is opt-in: it runs only when
both the binary (via `SENTRUX_BIN`) and a baseline in `ratchets.baselineDir` exist. Until then it
skips silently — safe to leave configured even if you haven't installed the tool yet.

## 5. (Optional) Bring your own structural rules

Language-specific structural rules (e.g. `ast-grep` for TS, custom linters) are **not** part of the
agnostic core — they're a bring-your-own add-on. See
[`../examples/worker-brain/.claude/skills/worker-ast-rules/`](../examples/worker-brain/.claude/skills/worker-ast-rules/)
for a worked TypeScript example you can adapt.

---

## Verify it works

```bash
# core/ must contain zero hardcoded language tool names:
grep -rIE 'tsc|knip|eslint|firestore' core/ && echo "LEAK" || echo "clean"

# read-config resolves your manifest:
python core/hooks/scripts/read-config.py gates.prePush.steps
```

Then make a trivial commit with a fake secret staged — the pre-commit gate should block it.

For a complete, real-world reference (every manifest key mapped to a live gate), read
[`../examples/worker-brain/`](../examples/worker-brain/).
