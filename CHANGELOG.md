# Changelog

Adopters: `core/` is copied, not linked. To update, re-copy `core/` over your
`.claude/core/` (never edit it downstream — project-specific behavior belongs
in `stack.json`, your own rules, or your own scripts) and diff
`settings.template.json` against your `settings.json` for new hooks.

## 1.4.0 — 2026-08-09

**Fixed — the documented install left every gate pointing at nothing**
- `docs/adoption.md` said to copy `core/` into `.claude/core/`, while
  `settings.template.json` invoked its hooks as `python core/hooks/scripts/…`
  relative to the project root — a directory the install never created. Python then
  exits 2 on the missing file, and **exit 2 means deny**: anyone who followed the
  guide ended up with every Bash call and every turn close blocked, by an error that
  never mentioned this framework. The template now resolves `.claude/core/…`,
  matching Step 1. **Adopters: diff `settings.template.json` against your
  `settings.json`.** If you installed `core/` somewhere else, edit the paths — and
  verify with the two commands now in Step 3 of the adoption guide.
- `secret-scan-guard.py` hardcoded the scanner path under the project root, so the
  same mismatch made `bash` fail — which the guard mapped to exit 2, denying *every*
  commit forever. It now resolves `secret-scan.sh` next to itself, and a missing
  scanner **allows** the commit with a loud message: a broken install is a setup
  error, not a detected secret, and must not masquerade as one.
- `core/CLAUDE.template.md` imported `@.claude/rules/operating-procedure.md`, a path
  the install never creates. Now `@.claude/core/rules/…`.

**Changed — the example mirrors a setup that was audited down by 78%**
- The source project audited every standing instruction (would an agent do this
  anyway? does a gate already cover it? does it conflict?) and cut always-loaded
  context from 11,381 to 2,466 words: 12 rules to 3, `CLAUDE.md` 3,300 to 551.
- `examples/nextjs-firebase/` now mirrors that: 6 rules moved to `archive/rules/`,
  and **the real `CLAUDE.md` is mirrored for the first time** — the manifest had no
  target for it, so the single biggest artifact of the setup never reached the
  example. `alert-engine-pattern`, `cron-security` and `regional-thresholds` stay
  mirrored from the source's archive: they carry domain facts no gate can recover.
- `commands/` (15) and 5 more scripts joined `sync-manifest.json`. They were never
  in it, so they drifted unseen — one command was 32% similar to its source.
- **This ratio does not transfer to `core/`.** There the rules are not loaded per
  session and every gate behind them is opt-in via `stack.json` (absent key = silent
  no-op), so a rule that is redundant in a wired repo is the only safety net in one
  without. Nothing was cut from `core/`.

**Added**
- `scripts/check-doc-sync.py` now fails if any file under
  `examples/*/{rules,commands,scripts}` is missing from that example's
  `sync-manifest.json` (declare it in `map`, or in the new `unsynced` list if it is
  example-only). The mirror had rotted for months and every gate stayed green —
  a gate that cannot see the drift is indistinguishable from no gate.
- Leak detection widened to `Worker[ _-]?Brain`, the source project's name and
  developer paths. It immediately caught two files that were already public.
- Three tests for `secret-scan-guard.py` (clean tree, staged secret → exit 2,
  non-commit ignored). It had **zero** coverage — precisely where the 1.3.2
  regression happened. Suite: 12 → 15 cases.

**Docs**
- Corrected counts that had drifted: 10 core rules (not 8), 6 core commands (not 5),
  12 hook scripts (not 7), and the example's real 6/6/6 hook split (not 3/6/4).
- The secret-scan section taught the harmless lesson (`PreToolUse` vs `PostToolUse`)
  and still described the *bug* — "blocks it (exit 1)". It now leads with the exit-2
  contract and names the wrapper that enforces it.
- Documented a known gap: `security.secretScan` is advertised as configurable but
  the guard never reads it. Better a documented gap than a false promise.

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
