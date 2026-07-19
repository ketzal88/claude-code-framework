# Changelog

Adopters: `core/` is copied, not linked. To update, re-copy `core/` over your
`.claude/core/` (never edit it downstream — project-specific behavior belongs
in `stack.json`, your own rules, or your own scripts) and diff
`settings.template.json` against your `settings.json` for new hooks.

## 1.3.2 — 2026-07-19

**Fixed**
- **`secret-scan` never blocked a commit — on any platform.** Claude Code denies a
  tool only on hook **exit 2**; exit 1 is treated as a non-blocking error and the
  tool runs anyway. `secret-scan.sh` exits 1 when it finds a secret, and the
  `settings.template.json` wrapper did `sys.exit(subprocess.call(...))`, propagating
  that 1 — so a `git commit` carrying a secret went straight through. The wrapper is
  now a real script (`core/hooks/scripts/secret-scan-guard.py`) that maps any
  non-zero scanner exit to 2. **Adopters must re-copy `core/` AND update the
  secret-scan `command` in their `settings.json`** (diff against
  `settings.template.json`).
- **`secret-scan.sh` silently passed everything on Windows.** With
  `core.autocrlf=true` and no `.gitattributes`, git checks out
  `core/security/secret-patterns.txt` with CRLF; the read loop left a trailing `\r`
  on every pattern, so `grep -E "PATTERN\r"` matched nothing. Patterns are now
  `\r`-stripped, and `.gitattributes` pins `*.sh` and `core/security/*.txt` to LF.

**Note for adopters:** these two bugs stacked — even after the CRLF fix the hook
still could not block, because of the exit code. Verify with a throwaway commit
carrying a fake key (e.g. an `AKIA...` example value): it must be denied.

## 1.3.1 — 2026-07-19

**Fixed**
- `secret-scan.sh` filename check no longer flags the framework's own scanner
  infrastructure. Staging `core/**` (exactly what adopters copy) — or the scanner
  script / pattern file anywhere — tripped the `*secret*` filename heuristic and
  blocked the commit with "looks like a secrets file". These files only *describe*
  secrets; they never hold them, so they are now exempt from the filename check
  (the content-pattern check still applies). Surfaced while adopting the framework
  into a new repo, where the very first commit of `core/` was blocked.
- `tests/test-core-guards.py` now covers `secret-scan.sh` (core/ infra exempt, a
  `.env` file still blocked; skips gracefully if bash is unavailable).

## 1.3.0 — 2026-07-15

**Added**
- `core/rules/subagent-economics.md` — the model tier is a decision, not a
  default. Declare `model:` on every agent definition (absent = inherits the most
  expensive tier); set the tier per stage in fan-out workflows; scale the agent
  count to the question. From a real measurement: subagent-heavy sessions were
  **81% of a day's usage and 69% of a week's**, while the static overhead
  everyone trims (system prompt, brain file, skills) did not register — it is
  cached at ~10%. Each subagent opens its own window and inherits none of the
  parent's cache, so cost scales with agent count × tier, and neither scales with
  how hard the question is.
- README Context Layer: the subagent half of the same problem, with the measured
  shares (150k+ context = 76–82% of usage; one workflow = 25% of a day; one MCP
  server's results = 13%).

## 1.2.0 — 2026-07-15

Context layer + codebase-graph layer. The framework had gates for correctness and
nothing for the context window itself — where the recurring cost actually lives.

**Added**
- `core/hooks/scripts/filter-verbose-output.sh` + `filter-verbose-guard.py` —
  collapse a verbose command's output to its verdict **when it passes** (a failure
  is never filtered), driven by `context.filterVerbose`. Absent key = no wrapping.
  Measured on the reference project: 5,928 → 34 tokens (−99.4%) and 3,219 → 58
  (−98.2%).
- `context.filterVerbose` in `stack.schema.json` / `stack.example.json`.
- README **Context Layer**: the four rules it encodes — a failure is never
  filtered; the exit code is authoritative (`cmd | grep` returns *grep's* status,
  inverting every gate that reads it); match exactly, never on substrings; and
  static content belongs in CLAUDE.md, never in a per-prompt hook (a
  `UserPromptSubmit` injection accumulates in history and is re-paid every turn —
  quadratic; static wins ~6x by turn 50). Plus the two measurement traps: cached
  content bills at ~10%, and `/context` over-counted MCP ~3x until Jan 2026.
- Codebase-graph layer (graphify): `core/commands/graphify.md`,
  `core/rules/graphify.md`, `core/hooks/scripts/stop-graphify-refresh.py`.
  Language-agnostic, needs no `stack.json`.

**Changed**
- `settings.template.json` wires `filter-verbose-guard.py` (non-blocking).

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
