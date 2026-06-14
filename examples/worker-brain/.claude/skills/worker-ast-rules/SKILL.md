---
name: worker-ast-rules
description: Use when auditing code quality in Worker Brain, reviewing a PR, adding a new alert engine or cron route, or when the user mentions "ast-grep", "enforcement", "architectural rules", or "audit patterns". Runs structural AST rules that enforce the project's invariants — pure evaluate() methods, cron auth, objective-utils usage, error reporting, and doc ID patterns. Auto-activates on audit / lint / code-quality tasks.
---

# Worker Brain — AST Rules

Structural enforcement of Worker Brain architectural invariants via `ast-grep`.

Where code review catches opinions, these rules catch **violations of rules the codebase already documents** (`.claude/rules/*.md`). Every rule here has a corresponding doc rule — if a rule stops making sense, the doc and rule both need to change.

## Prerequisites

Install ast-grep once per machine:

```bash
npm install -g @ast-grep/cli
# or: cargo install ast-grep
```

Verify:
```bash
ast-grep --version
```

## Running the rules

```bash
# From repo root
bash .claude/skills/worker-ast-rules/scan.sh
```

Exit code is non-zero if any `error`-severity rule matches. `warning` rules report but don't fail.

To run a single rule:
```bash
ast-grep scan --rule .claude/skills/worker-ast-rules/rules/no-firestore-in-evaluate.yml
```

To run over a single file:
```bash
ast-grep scan -c .claude/skills/worker-ast-rules/sgconfig.yml src/lib/alert-engines/google-alert-engine.ts
```

## Rules shipped

| Rule | Severity | Enforces | Doc source |
|---|---|---|---|
| `no-firestore-in-evaluate` | error | Pure `evaluate()` — zero DB access inside engine methods | `.claude/rules/alert-engine-pattern.md` |
| `cron-requires-auth` | error | Every `/api/cron/**` route references `validateCronSecret` | `.claude/rules/cron-security.md` |
| `cron-must-declare-maxDuration` | warning | Every cron route exports `maxDuration` | `.claude/rules/cron-security.md` |
| `no-hardcoded-conversion-metric` | warning | No direct `metrics.purchases` / `metrics.leads` — use `getPrimaryMetric()` | `.claude/rules/alert-engine-pattern.md` |
| `no-console-error-swallow` | warning | `catch` blocks must call `reportError` — not just `console.error` | `.claude/rules/cron-security.md` |
| `no-null-as-delete-sentinel` | warning | `.update({ field: null })` — should use `FieldValue.delete()` | `.claude/rules/firestore-conventions.md` |

## How rules are structured

Each rule is a YAML file in `rules/`:

```yaml
id: rule-name
language: TypeScript
severity: error
message: Human-readable explanation with link to the doc.
rule:
  # ast-grep pattern — see https://ast-grep.github.io/guide/rule-config.html
  pattern: $PATTERN
  inside:
    kind: method_definition
    has:
      field: name
      pattern: evaluate
```

Metavariables (`$FOO`, `$$$ARGS`) match AST nodes structurally. This is why a rule like "no firestore in evaluate" won't false-positive on a comment mentioning `db.collection`.

## When to add a new rule

Add a rule when **all three** are true:
1. The invariant is already documented in `.claude/rules/*.md` or `CLAUDE.md`.
2. You've seen it violated at least once (past commit, PR, incident).
3. The violation is structural (shape of the code), not semantic (logic is wrong).

Don't add rules for:
- Style preferences (use Prettier/ESLint).
- Semantic bugs (use tests).
- Things that need human judgment (use code review).

## Integration points

- **Pre-commit hook**: wire `scan.sh` into `.claude/settings.json` PreToolUse on `git commit` to block violations.
- **CI**: add to GitHub Actions as a separate job — fails PR on error-severity hits.
- **Slash command**: `/audit-ast` could run the full scan and summarize hits.

Pick integration based on rule maturity: new rules start as `warning` and only get promoted to CI/hook gates once they've been quiet for a few weeks.
