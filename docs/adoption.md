# Adopting the Claude Code Framework

This guide walks you through wiring the framework into any project — TypeScript, Python, Go,
Java, or any other language. **Time:** ~30 minutes for the core gates.
Domain-specific rules and commands are additive and can come later.

---

## Step 1: Copy the core

```bash
cp -r core/ your-project/.claude/core/
```

`core/` is entirely language-agnostic. No edits needed.
It contains:
- `CLAUDE.template.md` — brain template with `{{placeholders}}`
- `rules/` — 8 universal rules (operating-procedure, ratchet-philosophy, security-gates, commands-encode-workflows, close-protocol, environment-canonical, incident-triage, learning-loop)
- `commands/` — 5 universal slash commands
- `hooks/` — hook scripts and settings template
- `security/` — secret patterns and SAST adapter docs

Sanity-check the hook guards anytime with `python tests/test-core-guards.py`.

---

## Step 2: Write your stack.json

Create `stack.json` at the **project root** (not inside `.claude/`). Start minimal:

**Minimal — secret scan + one check:**
```json
{
  "language": "python",
  "commands": {
    "typecheck": "mypy ."
  },
  "security": {
    "secretScan": ".claude/core/hooks/scripts/secret-scan.sh"
  },
  "gates": {
    "preCommit": { "secretScan": "blocking" }
  }
}
```

**Full TypeScript example** → `examples/nextjs-firebase/stack.json`

Key rule: **absent key = gate silently skipped**. Never required to fill all keys.
Adopt incrementally — each gate you add is independent.

---

## Step 3: Wire settings.json

```bash
cp .claude/core/hooks/settings.template.json .claude/settings.json
```

The template pre-wires:
- `PreToolUse` (Bash): `canonical-guard.py` — **blocking** (reads `environment.forbiddenCommands`; no-op if absent)
- `PreToolUse` (Bash `git push`): `pre-push-guard.py` — **blocking** (push policy + quality gate)
- `PreToolUse` (Bash `git commit`): `secret-scan.sh` — **blocking**
- `Stop`: `ratchet-guard.py` (dead-code ratchet, scope-by-diff) — **blocking**
- `Stop`: `close-guard.py` (close protocol) — **blocking once** (no-op unless `gates.closeProtocol: "blocking"`)

All `PreToolUse` hooks run **before** the tool action completes, so they can
actually block. The secret scan must be `PreToolUse` — `PostToolUse` fires after
the commit is done and `git diff --cached` is already empty.

Adjust script paths if your scripts live somewhere other than `.claude/core/hooks/scripts/`.

---

## Step 4: Create your CLAUDE.md

```bash
cp .claude/core/CLAUDE.template.md .claude/CLAUDE.md
```

Fill the `{{placeholders}}`:
- `{{PROJECT_NAME}}`, `{{LANGUAGE}}`, `{{FRAMEWORK}}`
- `{{TEST_COMMAND}}`, `{{LINT_COMMAND}}`, `{{BUILD_COMMAND}}`
- Architecture section: key patterns, file structure, important invariants

The `@.claude/core/rules/` import syntax works immediately — no build step. Example:
```markdown
@.claude/core/rules/ratchet-philosophy.md
@.claude/core/rules/security-gates.md
```

---

## Step 5: Freeze baselines (one-time)

Each ratchet requires an initial baseline commit. The baseline is the floor:
once committed, the metric can only decrease.

**Dead-code ratchet** (if using `ratchets.deadCode`):
```bash
# TypeScript (knip)
npx knip
node scripts/check-dead-code-baseline.js --write
git add .dead-code-baseline.json && git commit -m "chore: freeze dead-code baseline"

# Python (vulture)
vulture src/ --min-confidence 80 > .vulture-baseline.txt
git add .vulture-baseline.txt && git commit -m "chore: freeze dead-code baseline"
```

**Structural ratchet / sentrux** (if using `ratchets.structural`):
```bash
export SENTRUX_BIN=/path/to/sentrux
sentrux baseline .  # creates .sentrux/baseline.json
git add .sentrux/ && git commit -m "chore: freeze sentrux baseline"
```

---

## Step 6: Add domain rules

Domain rules go in `.claude/rules/` (your project, not in `core/`). Each rule captures
an invariant specific to your codebase.

**When to create a rule:**
- You corrected Claude for the same thing twice
- There's an architectural invariant that must always hold
- The rule is not obvious from the code itself

See `examples/nextjs-firebase/rules/` for 12 production domain rules across:
alert engine contracts, cron security, database conventions, error patterns, regional
thresholds, environment canonical paths, UI delivery checklists and incident triage.

---

## Step 7: Add domain commands

Domain commands go in `.claude/commands/`. Each encodes a multi-step workflow.

**When to create a command:**
- You run the same 3+ commands in sequence repeatedly
- There's a workflow with built-in safety checks
- The workflow involves multiple files, services, or confirmation steps

See `examples/nextjs-firebase/commands/` for 15 production slash commands:
from alert scaffolding to Firestore index deploy to AI prompt versioning.

---

## Verification

```bash
# Verify the executable core has no hardcoded tool names
# (rules may cite tools as illustrative examples; the scripts never do)
grep -rIE 'tsc|knip|eslint|firestore' .claude/core/hooks/scripts/
# Must return empty

# Verify read-config works
python .claude/core/hooks/scripts/read-config.py commands.typecheck
# Should print your typecheck command

# Verify pre-push guard reads the manifest
python .claude/core/hooks/scripts/pre-push-guard.py <<'EOF'
{"tool_input": {"command": "git push origin main"}, "session_id": "test"}
EOF
# Should list the steps it would run
```

---

## Reference: ExampleApp

`examples/nextjs-firebase/` is the full, faithful reference for a TypeScript/Next.js 14/Firebase/Vercel
production SaaS. Use it to understand what a fully-adopted setup looks like:

- A complete `stack.json` with all gates wired (8 commands, design + cron-doc gates, sentrux, push policy, close protocol, forbidden commands)
- 12 domain rules across alert engines, cron security, Firestore conventions, currency thresholds, environment paths, UI delivery, incident triage
- 15 slash commands from scaffolding to backfill to AI prompt versioning
- 13 hooks: 3 blocking `PreToolUse`, 6 advisory `PostToolUse`, 4 blocking `Stop`
- 13 production scripts (guards, baseline checkers, dev-up) and TypeScript ast-grep rules as an optional add-on
- `sync-manifest.json` — update the mirror from the source project in 1 command: `python scripts/sync-example.py <project-root> examples/nextjs-firebase` (sanitization + leak check built in)

---

## Troubleshooting

**`read-config.py` exits 1 for every key**
→ `stack.json` is not in the project root or any ancestor directory (searched up to 10 levels).

**Pre-push guard runs even for docs-only changes**
→ Set `SKIP_PREPUSH=1`. Allowed only when all changed files are `.md`, `.claude/**`, `docs/**`,
`.gitignore`. The guard enforces this and rejects the bypass for code changes.

**Ratchet-guard blocks every turn**
→ A dead-code ratchet regressed. Either delete the orphan export, wire it to a consumer,
or run `--write` to lower the baseline if you genuinely cleaned up other files.

**sentrux gate blocks on a clean push**
→ A structural metric regressed vs `.sentrux/baseline.json`. Run `sentrux diff .` to diagnose,
fix the regression, then re-push. If sentrux isn’t installed, remove it from `gates.prePush.steps`.

**Secret scan false-positives**
→ Edit `core/security/secret-patterns.txt` to narrow the pattern, or add a file exemption
to `check-no-secrets.sh`. Patterns are tuned to avoid `TODO|PLACEHOLDER` values.
