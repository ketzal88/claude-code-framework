# Changelog

Adopters: `core/` is copied, not linked. To update, re-copy `core/` over your
`.claude/core/` (never edit it downstream — project-specific behavior belongs
in `stack.json`, your own rules, or your own scripts) and diff
`settings.template.json` against your `settings.json` for new hooks.

## 1.1.0 — 2026-07-03

Session-friction layer, from an audit of 100+ production sessions.

**Added**
- `core/hooks/scripts/canonical-guard.py` — blocks commands that always fail
  on this machine (`environment.forbiddenCommands`) with the fix inline.
- `core/hooks/scripts/close-guard.py` — close-protocol Stop hook
  (`gates.closeProtocol: "blocking"`).
- `gates.push: "operator-only"` in `pre-push-guard.py` — the agent never
  pushes; every `git push` blocks instantly with the close instruction.
- `CHANGED_FILES` scope-by-diff contract in `ratchet-guard.py` — ratchets can
  block only on the session's own regressions; inherited debt warns.
- Core rules: `close-protocol.md`, `environment-canonical.md`,
  `incident-triage.md` (living error dictionary), `learning-loop.md`.
- `tests/test-core-guards.py` — dependency-free smoke suite for the guards.
- `scripts/sync-example.py` + per-example `sync-manifest.json` — 1-command
  mirror update from a real project, with sanitization + leak check built in.
- `scripts/check-doc-sync.py` — the framework's own doc-sync gate.
- CI workflow: compile + guard tests + doc-sync + JSON/schema validation.

**Changed**
- Reference example renamed to `examples/nextjs-firebase/` and fully
  anonymized (no company, product, client or person names) — the framework
  is generic and copyable to any project.
- `settings.template.json` wires the two new hooks.
- `stack.schema.json` / `stack.example.json`: `environment.forbiddenCommands`,
  `gates.push`, `gates.closeProtocol`.

## 1.0.0 — 2026-06

Initial release: config-driven core (`stack.json` + `read-config.py`),
secret-scan (PreToolUse), pre-push quality gate, dead-code ratchet Stop hook,
security-review layer, CLAUDE.template.md, and the reference example.
