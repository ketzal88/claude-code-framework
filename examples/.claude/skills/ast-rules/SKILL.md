---
name: ast-rules
description: Structural AST enforcement of architectural invariants via ast-grep.
---

# AST Rules

Run: `bash .claude/skills/ast-rules/scan.sh`

| Rule | Severity | Catches |
|---|---|---|
| `no-db-in-evaluate` | error | DB calls inside evaluate() |
| `cron-requires-auth` | error | Cron missing auth check |
