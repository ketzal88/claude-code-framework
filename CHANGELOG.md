# Changelog

Adopters: `core/` is copied, not linked. To update, re-copy `core/` over your
`.claude/core/` (never edit it downstream — project-specific behavior belongs
in `stack.json`, your own rules, or your own scripts) and diff
`settings.template.json` against your `settings.json` for new hooks.

## 1.5.7 - 2026-11-26

Security: 1.5.6 decided whether to trust an alias from raw text, which quoting (`git conf''ig ...`) or a changed `PATH` could fool (review of 1.5.6).

- `git_target.py`: only git builtins are trusted. Any other subcommand (an alias, an external `git-*` like `git lfs`) is OPAQUE, with no alias lookup and no text filter. Under `gates.push: "operator-only"` that blocks `git <alias>` and external git commands; the secret scan runs on them.
- Tests: 82 cases.

## 1.5.6 - 2026-11-26

Security: alias resolution now fails closed (review of 1.5.5).

- `git_target.py`: a non-builtin subcommand is OPAQUE when the same command can change git config (`git config`, `GIT_CONFIG*`, `GIT_DIR`, `HOME=`, `XDG_CONFIG_HOME`, `--config-env`, `include`, a `.git/` path), so `git config alias.p push && git p` and `GIT_CONFIG_COUNT=1 ... git p` are caught. Taint carries across segments and into nested shells.
- `git_target.py`: `--config-env=alias.*` is treated like `-c alias.*`.
- `git_target.py`: alias lookup fails closed: an error, an expansion that does not start with a known subcommand (`-c x push`) or an unknown name gives OPAQUE. External `git-*` commands on PATH (`git lfs`) still resolve.
- Tests: 80 cases.

## 1.5.5 - 2026-11-26

Security: three ways to hide a push from the guards, found in review.

- `git_target.py`: shell reserved words before git (`!`, `if`, `then`, `else`, `elif`, `do`, `while`, `until`, `{`) are dropped, so `! git push` and `if git push; then :; fi` are seen.
- `git_target.py`: `git -c alias.*` yields OPAQUE; an alias already in git config is expanded to its real subcommand (a shell alias `!...` yields OPAQUE). Builtins are never resolved as aliases, like git itself.
- `pre-push-guard.py`: `is_dry_run` lets the last flag win, so `git push -n --no-dry-run` is a real push. OPAQUE calls always count as a push (the old `"push" in cmd` check missed config aliases).
- Tests: 71 cases.

## 1.5.4 - 2026-11-26

- `secret-patterns.txt`: Google API keys (`AIza...`), upstreamed from an
  adopter that had it as a project pattern.

## 1.5.3 - 2026-11-26

Push policy across nested repos, and reporting unpushed commits at close.

- `pre-push-guard.py`: the root `stack.json` is the floor. 1.5.2 read the
  policy only from the first push target's manifest, so a nested
  `{"gates": {}}` dropped `operator-only`, and the second push of
  `git push && git -C sub push` was never checked. Now every target is
  checked against the root and its own manifest (either one saying
  `operator-only` blocks), checks run per target, and a target without
  `prePush.steps` inherits the root's.
- `git_target.py`: `--git-dir` and `--work-tree` (also in `=` form) move the
  target directory like `-C`.
- `close-guard.py`: new `gates.closeUnpushed: "report"`. Commits ahead of
  upstream (root and nested repos) trigger the reminder even with a clean
  tree; the agent reports them instead of pushing. Added to the schema.
- Tests: 62 cases (policy floor, multi-target, `--git-dir`/`--work-tree`,
  close report on a bare-remote fixture).

## 1.5.2 - 2026-11-26

Second security pass on the command parser, and per-repo manifests on push.

- `git_target.py`: `{` and `}` only split a command when they stand alone as a
  word, so `git commit -m{x} -a` keeps its `-a`. Wrapper options that take a
  value are consumed (`sudo -u git git commit`), `env -S "..."`, `eval "..."`
  and `bash -o opt -c "..."` are read as nested commands. A git call the parser
  cannot see into (nested deeper than 3 levels, `bash -c` with no readable
  string) comes back as `OPAQUE` and the guards assume the worst.
- `secret-scan-guard.py`: deny by default. Any `git commit` option the guard
  does not know (`--pathspec-from-file`, a future flag) triggers the pending
  scan; only a short list of known-safe flags keeps the staged-only scan.
- `pre-push-guard.py`: reads `stack.json` from the directory the push runs in,
  so a nested repo with its own manifest gets its own gates (one without a
  manifest falls back to the parent's). An opaque git call next to the word
  `push` is treated as a push.
- Tests: 55 cases (11 new).

## 1.5.1 - 2026-11-26

**Fixed: five ways around the 1.5.0 gates** (found by a security review of 1.5.0)
- `secret-scan-guard.py`: `git commit -m x -a` and `git commit -m x <path>`
  were read as staged-only commits, because parsing stopped at `-m`. Option
  values are now skipped, and `-a`, `-i`, `-o` and any pathspec mean a
  pending scan.
- `secret-scan-guard.py`: `git -C sub add -A && git commit` compared
  directories, saw two different ones and scanned only the index. Any
  add/stage/rm/mv in the command now makes every commit in it pending.
- `secret-scan-guard.py`: a commit in a directory the same command creates
  was skipped. It now blocks and asks for the commit in a separate call.
- `git_target.py`: `env git ...`, `command`/`exec`/`nohup`/`sudo`/`time`
  prefixes, `bash -c "..."` and `( ... )` / `{ ...; }` groups hid the git
  word. All are unwrapped now.
- `pre-push-guard.py`: `git push -o -n` was taken as a dry run because `-n`
  appeared anywhere in the args. Only a real `-n` / `--dry-run` flag counts.
- `secret-scan.sh`: untracked files over 1 MB were skipped in pending mode.
  They are scanned now (streamed, binaries still skipped).
- Tests: 44 cases.

## 1.5.0 - 2026-11-26

**Adopters:** re-copy `core/` (two new shared modules, `git_target.py` and
`session_files.py`, must sit next to the hooks). No `settings.json` change is
required. If your copy of `secret-scan-guard.py` exits 1 on a hit, or your
graphify Stop hook spawns an inline `python -c`, you are on a pre-1.4 copy:
re-sync, because neither blocks or refreshes reliably.

**Fixed: gates that a compound command walked around**
- `secret-scan-guard.py` only scanned commands that *started* with
  `git commit`. `git add -A && git commit`, `cd repo && git commit` and
  `git -C repo commit` went unscanned. It now finds the commit in any segment
  (`git_target.py`) and, when the add has not run yet (or with `commit -a`),
  scans pending files: unstaged and untracked.
- `secret-scan.sh` scans added lines only (deleting a secret no longer
  blocks), uses NUL-separated file lists, allows `.env.example`-style
  templates, and honors `secret-scan:allow` / `gitleaks:allow` markers.
  `secret-patterns.txt` widened.
- `pre-push-guard.py` finds a push anywhere in the command, and the new
  `gates.pushWrappers` (regexes) applies the push policy to project scripts
  that push for you. prePush steps are skipped for a wrapper with no real
  `git push` of its own.

**Fixed: guards that blamed this session for another session's files**
- `close-guard.py` is session-scoped: only files this session edited,
  committed or named in its commands can block (`session_files.py`, from the
  transcript). Foreign dirty files are counted, never listed as yours. Falls
  back to the whole tree if the transcript is unreadable. Also checks repos
  nested one level down and reports commits ahead of upstream.
- `ratchet-guard.py` scopes to files this session touched, including ones it
  already committed, so an early commit no longer escapes the ratchet.

**Fixed: graph refresh**
- `stop-graphify-refresh.py` also refreshes when graph.json `built_at_commit`
  differs from `HEAD`, runs its worker as a script file instead of inline
  `python -c`, and uses `CREATE_NO_WINDOW` on Windows.

**Added**
- `environment.forbiddenCommands[].unless`: optional regex that suppresses a
  rule (tools broken in only one mode).
- Rules: `context-economics.md` (re-reading context is the bill; compaction
  loops from nested brain files and heavy MCP schemas), `evidence-states.md`
  (six states, verify in the destination, canaries for advisory gates),
  `headless-automation.md` (child sessions, scheduled jobs, hooks).
- `subagent-economics.md`: model/effort table per task. Updates to
  close-protocol, ratchet-philosophy, security-gates, environment-canonical,
  graphify, learning-loop and operating-procedure.
- Tests: compound/`-C`/`cd` commits, pending scan, deleted secret,
  `.env.example`, allow marker, push wrappers, `unless`, session-scoped
  close-guard with a fake transcript (33 cases).
- Hook scripts are ASCII-only (cp1252 consoles).

**Next (not in this release):** a SessionStart hook that syncs the checkout
before work, and a UI smoke gate.

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
