---
name: nextjs-firebase-ast-rules
description: Structural AST enforcement of ExampleApp architectural invariants via ast-grep.
---

# AST Rules

Run: `bash examples/nextjs-firebase/ast-rules/scan.sh`

These rules enforce the invariants documented in `examples/nextjs-firebase/rules/`.
They require [ast-grep](https://ast-grep.github.io/) to be installed.

| Rule | Severity | Catches |
|---|---|---|
| `no-db-in-evaluate` | error | `db.collection()` inside any `evaluate()` method — breaks pure-computation contract |
| `cron-requires-auth` | error | Cron route missing `validateCronSecret` reference |

When to add a new rule:
1. The invariant is already documented in `examples/nextjs-firebase/rules/*.md`
2. You've seen it violated at least once
3. The violation is structural (code shape), not semantic (logic)

See `core/security/README.md` for SAST tool adapters (semgrep, bandit, gosec) —
these ast-grep rules are a complement, not a replacement.
