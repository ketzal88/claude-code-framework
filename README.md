# Claude Code Framework — Language-Agnostic, Config-Driven

A layered enforcement system for Claude Code that works with **any language or framework**.
Three layers: a universal `core/` that reads a per-project `stack.json` manifest, a reference
example for TypeScript/Next.js/Firebase ([ExampleApp](examples/nextjs-firebase/)), and a security
layer (secret-scan, blocking pre-push gate, SAST, dep-audit) driven entirely by the manifest.

---

## Table of Contents

1. [Philosophy](#philosophy)
2. [Architecture](#architecture)
3. [stack.json — The Manifest](#stackjson--the-manifest)
4. [Security Layer](#security-layer)
5. [Codebase Graph Layer](#codebase-graph-layer)
6. [Context Layer](#context-layer)
7. [Core Layer](#core-layer)
8. [ExampleApp Reference Example](#exampleapp-reference-example)
9. [Adopting This Framework](#adopting-this-framework)

---

## Philosophy

Four principles:

1. **Config-driven, not code-forked.** A Java project and a Python project use the same hooks, commands, and gates — only `stack.json` differs. No per-language copies, no conditional logic in `core/`.
2. **Absent key = safe skip.** Every gate reads its command from the manifest. Missing key → silent no-op. Adoption is additive: start with nothing, grow the manifest as you wire each gate.
3. **The baseline is the floor.** Quality ratchets (dead-code, structural, any-type, design) enforce that metrics never grow. The baseline can go down; it never goes up.
4. **Commands encode workflows.** Multi-step processes become slash commands so the methodology runs without the operator invoking anything manually.

---

## Architecture

```
Universal gate  ──reads──►  stack.json  ──runs──►  the command for THIS project
(secret-scan,               (declares test,        (tsc / mvn test / pytest / go test)
 pre-push, ratchets)         lint, sast, ratchets…)
```

| Layer | Path | What it contains |
|---|---|---|
| **Core** | `core/` | Language-agnostic rules, command templates, hook scripts, security layer. Zero hardcoded tool names. |
| **Manifest** | `stack.json` | Per-project configuration. The only file an adopter must write. |
| **Reference** | `examples/nextjs-firebase/` | Faithful mirror of a real production TypeScript/Next.js/Firebase setup. |

### Repository Structure

```
claude-code-framework/
├─ README.md
├─ VERSION / CHANGELOG.md     # adopters re-copy core/ to update
├─ stack.schema.json          # validates any stack.json
├─ stack.example.json         # blank template
├─ .github/workflows/ci.yml   # compile + guard tests + doc-sync + schema validation
├─ core/
│  ├─ CLAUDE.template.md      # brain template with {{placeholders}}
│  ├─ rules/
│  │  ├─ operating-procedure.md
│  │  ├─ ratchet-philosophy.md
│  │  ├─ security-gates.md
│  │  ├─ commands-encode-workflows.md
│  │  ├─ close-protocol.md            # how every substantial turn must end
│  │  ├─ environment-canonical.md     # one true path per operation, enforced
│  │  ├─ incident-triage.md           # protocol + living error dictionary
│  │  └─ learning-loop.md             # persistent memory that actually persists
│  ├─ commands/
│  │  ├─ commit-checkpoint.md
│  │  ├─ ci-simulate.md
│  │  ├─ typecheck.md
│  │  ├─ env-check.md
│  │  └─ security-review.md
│  └─ hooks/
│     ├─ settings.template.json
│     └─ scripts/
│        ├─ read-config.py       # manifest reader — heart of config-driven
│        ├─ secret-scan.sh       # agnostic regex secret scanner
│        ├─ pre-push-guard.py    # gates.prePush.steps + gates.push=operator-only; BLOCKING
│        ├─ ratchet-guard.py     # generic baseline ratchet (Stop hook) + CHANGED_FILES scope
│        ├─ canonical-guard.py   # blocks environment.forbiddenCommands with the fix inline
│        ├─ close-guard.py       # close-protocol: uncommitted code at Stop reminds once
│        └─ sast-scan.sh         # runs security.sast
├─ core/security/
│  ├─ secret-patterns.txt
│  └─ README.md               # SAST adapter docs
├─ scripts/
│  ├─ sync-example.py         # 1-command mirror update from a real project (sanitizing)
│  └─ check-doc-sync.py       # the framework's own doc-sync gate (runs in CI)
├─ tests/
│  └─ test-core-guards.py     # dependency-free smoke suite for the hook guards
└─ examples/
   └─ nextjs-firebase/
      ├─ stack.json             # fully-filled TypeScript/Next.js/Firebase manifest
      ├─ settings.json          # production .claude/settings.json (anonymized)
      ├─ sync-manifest.json     # file map + sanitization rules for sync-example.py
      ├─ rules/                 # 12 domain rules (anonymized from production)
      ├─ commands/              # 15 slash commands (anonymized from production)
      ├─ ast-rules/             # optional TypeScript ast-grep rules
      └─ scripts/               # 13 production scripts (guards, checkers, dev-up)
```

---

## stack.json — The Manifest

Every project that adopts this framework authors one `stack.json` at the project root.
Each key is **optional** — an absent key means the gate is **silently skipped**.
Start with one gate and expand.

```json
{
  "language": "typescript",
  "packageManager": "npm",
  "commands": {
    "typecheck": "npx tsc --noEmit",
    "lint":      "npm run lint",
    "test":      "npm run test:unit",
    "build":     "npm run build"
  },
  "security": {
    "secretScan": "core/hooks/scripts/secret-scan.sh",
    "sast":       "",
    "depAudit":   "npm audit --audit-level=high"
  },
  "ratchets": {
    "deadCode":   "node scripts/check-dead-code-baseline.js",
    "structural": "sentrux gate",
    "baselineDir": ".sentrux/"
  },
  "gates": {
    "preCommit": { "secretScan": "blocking" },
    "prePush":   { "blocking": true, "steps": ["typecheck", "lint", "test"] },
    "push": "operator-only",
    "closeProtocol": "blocking"
  },
  "environment": {
    "forbiddenCommands": [
      { "pattern": "(^|[;&|]\\s*)(npx\\s+)?eslint\\b",
        "fix": "Global ESLint fails without eslint.config here. Use: npm run lint" }
    ]
  },
  "paths": {
    "source": ["src/**"],
    "codeExtensions": [".ts", ".tsx"]
  }
}
```

**Session-friction layer** (added 2026-07, from an audit of 100+ production sessions):
`gates.push: "operator-only"` makes every agent `git push` block instantly with the correct
close instruction (the push belongs to the human operator); `gates.closeProtocol: "blocking"`
reminds once when a turn ends with uncommitted code; `environment.forbiddenCommands` blocks
the commands that always fail on this machine with the fix inline (0-turn self-correction);
and `ratchet-guard.py` now passes `CHANGED_FILES` so ratchet commands can block only on
regressions the session itself introduced, downgrading inherited debt to a warning (CI still
enforces the global floor). Rules: `core/rules/close-protocol.md`,
`core/rules/environment-canonical.md`, `core/rules/incident-triage.md`.

Validated by `stack.schema.json`. See `stack.example.json` for a blank template.

**Language examples:**

| Language | `typecheck` | `lint` | `test` | `depAudit` |
|---|---|---|---|---|
| TypeScript | `npx tsc --noEmit` | `npm run lint` | `npm run test:unit` | `npm audit --audit-level=high` |
| Python | `mypy .` | `ruff check .` | `pytest -q` | `pip-audit` |
| Go | `go vet ./...` | `golangci-lint run` | `go test ./...` | `govulncheck ./...` |
| Java | `mvn -q compile` | `mvn checkstyle:check` | `mvn test` | `mvn dependency-check:check` |
| Rust | `cargo check` | `cargo clippy` | `cargo test` | `cargo audit` |

---

## Security Layer

All gates are driven entirely by `stack.json`. None are hardcoded — all adapt via the manifest.

| Gate | Hook Type | Blocking? | Manifest Key |
|---|---|---|---|
| **Secret scan** | `PreToolUse` (Bash `git commit`) | ✅ Yes — blocks the commit | `security.secretScan` |
| **Push policy (operator-only)** | `PreToolUse` (Bash `git push`) | ✅ Yes — instant, incl. `--no-verify` | `gates.push` |
| **Pre-push quality gate** | `PreToolUse` (Bash `git push`) | ✅ Yes — blocks the push | `gates.prePush.steps` |
| **Canonical commands** | `PreToolUse` (Bash) | ✅ Yes — with the fix inline | `environment.forbiddenCommands` |
| **Structural ratchet (sentrux)** | Pre-push step | ✅ Yes — as a step | `ratchets.structural` |
| **SAST / dep-audit** | Configurable | Configurable | `security.sast` / `security.depAudit` |
| **Security review (guided)** | On-demand (`/security-review`) | No — human/AI review | `security.review` |

### Secret Scan — PreToolUse (not PostToolUse)

`core/hooks/scripts/secret-scan.sh` intercepts `git commit` via **`PreToolUse`** and blocks it
(exit 1) if staged files match secret patterns.

**Why `PreToolUse` and not `PostToolUse`?** `PostToolUse` fires *after* the commit completes.
At that point `git diff --cached` is already empty — no staged changes to scan.
A secret-scan hook wired as `PostToolUse` is a no-op. The correct event is `PreToolUse`.

Patterns detected (from `core/security/secret-patterns.txt`): PEM private keys, AWS AKIA tokens,
Google OAuth credentials, Anthropic `sk-ant-` tokens, OpenAI `sk-proj-` tokens, Slack `xox*`
tokens, Meta long-lived tokens, GitHub PATs, Stripe live/test keys.

### Pre-Push Quality Gate — Blocking

`core/hooks/scripts/pre-push-guard.py` intercepts `git push` via **`PreToolUse`** and **blocks it**
(exit 2) if any configured step fails. It reads `gates.prePush.steps` from `stack.json` and
resolves each step as either a `commands.<step>` or `ratchets.<step>` entry. All steps run
regardless of individual failures (mirrors CI `if: always()`) so every problem surfaces in a
single pass.

**This gate is blocking.** It is `PreToolUse`, returns exit code 2, and aborts the push.
Describing it as “advisory” is incorrect.

`SKIP_PREPUSH=1` bypass is permitted **only** when all changed files match CI `paths-ignore`
patterns (`.md`, `.claude/**`, `docs/**`, `.gitignore`). Rejected for any code change.

### Structural Ratchet (sentrux)

[sentrux](https://github.com/your-org/sentrux) is a **structural-regression ratchet**, not a SAST
scanner. It runs as the last step of the pre-push gate (`ratchets.structural` in `stack.json`),
comparing the codebase against a committed baseline (`ratchets.baselineDir/baseline.json`).
If the structural metric regressed vs the baseline, the push is blocked.

**sentrux is opt-in and skips silently when unconfigured.** The binary is resolved via the
`SENTRUX_BIN` env var (default `C:\tmp\sentrux\sentrux.exe`). If the binary or the baseline
file is absent, the step is a no-op — safe to list in `stack.json` before installing.

sentrux belongs to `ratchets.structural`, **not** to `security.sast`.
The `security.sast` slot is reserved for one-shot SAST tools like semgrep or bandit.

### SAST / Dep-Audit

`core/hooks/scripts/sast-scan.sh` reads `security.sast` from the manifest and runs it.
Absent or empty → no-op.

| Language | SAST Tool | `security.sast` value |
|---|---|---|
| TypeScript/JS | semgrep | `semgrep --config auto src/` |
| Python | bandit | `bandit -r . -q` |
| Go | gosec | `gosec ./...` |
| Java/Kotlin | semgrep | `semgrep --config auto src/` |
| Ruby | brakeman | `brakeman --no-pager -q` |

Dep-audit follows the same pattern: set `security.depAudit` to your package manager's audit
command. See `core/security/README.md` for full adapter documentation.

---

## Codebase Graph Layer

An optional, language-agnostic layer built on [graphify](https://github.com/Graphify-Labs/graphify):
tree-sitter parses the codebase into a queryable knowledge graph of entities and their
`imports`/`contains` edges. It answers "who uses this?", "how does A reach B?", and "where do I
start?" via graph traversal instead of a file-by-file crawl.

| Property | Value |
|---|---|
| **Token cost** | Zero — AST extraction is local, no LLM, no API key |
| **Config** | **None** — tree-sitter covers 36+ languages, so it needs no `stack.json` |
| **Setup** | `uv tool install graphifyy && graphify install` |
| **Build / refresh** | `graphify update .` (gitignore `graphify-out/`) |
| **Query** | `graphify explain "X"` (blast radius) · `path "A" "B"` (trace) · `query "..."` (orient) |

Wiring: `core/commands/graphify.md` (usage), `core/rules/graphify.md` (when to consult, and the
honest limits), `core/hooks/scripts/stop-graphify-refresh.py` (optional Stop hook that backgrounds a
refresh after code-touching turns).

**Two honest caveats.** (1) The graph is a map of *imports*, not *runtime dependencies* — it does not
see HTTP calls, shared database tables, or event flows, so disconnected islands are usually real
decoupling, not a bug. Orient with it, then read the real code. (2) It is **net token-positive on
large exploration-heavy repos** but the aggressive auto-consult hooks add a small per-operation tax;
on small repos where grep suffices, keep it on-demand rather than always-on.

---

## Context Layer

Every token in the context window is paid for on every message. The expensive part is rarely
what you notice — it is the **recurring** cost: a verbose command that spends thousands of
tokens to say "all green", on every run, then sits in the transcript being re-read on every
later turn.

### Collapse verbose output when it passes

Opt in per project via `stack.json`:

```json
{
  "context": {
    "filterVerbose": ["npm run test:unit", "npm run test:alerts"]
  }
}
```

`core/hooks/scripts/filter-verbose-guard.py` (PreToolUse/Bash) wraps exactly those commands in
`filter-verbose-output.sh`, which collapses the output **only when the command passes**. Absent
key = no wrapping, silently.

Measured on the reference project:

| Command | Before | After | |
|---|---:|---:|---:|
| `npm run test:unit` | 5,928 tok (370 lines) | 34 tok | −99.4% |
| `npm run test:alerts` | 3,219 tok (194 lines) | 58 tok | −98.2% |

Do **not** list typecheck or lint: they are already quiet when green, and when they fail you
want the whole error.

### Four rules this layer encodes

**1. A failure is never filtered.** The full output is exactly what you need when something
breaks. A blind grep strips the context at the worst possible moment. Collapse on success only.

**2. The exit code is authoritative, text markers are not.** `cmd | grep` returns *grep's*
status — a broken run reports green, and a passing run reports broken (grep exits 1 when it
matches nothing). Any gate reading that exit code silently inverts. Capture `rc` before any pipe.

**3. Match exactly; never on substrings.** A rule that fires on substrings matches `test:unit`
inside `test:unittest`. The same class of bug: an unanchored `Error:` matches inside
`RangeError:` — and test suites legitimately print expected errors (one asserting an
invalid-timezone fallback prints `RangeError: Invalid time zone` **and passes**). That false
positive is why this wrapper trusts the exit code first.

**4. Static content belongs in CLAUDE.md, never in a per-prompt hook.** This is the big one.
A `UserPromptSubmit` hook injects *alongside the prompt* — at the tail of the message array —
so its text **accumulates in the history and is re-paid on every later turn**. Cost is
quadratic. Roughly: 10k of static rules vs 2k injected per turn crosses over at ~6 turns; by
turn 50 the static file wins by ~6x while injecting 5x less per turn. Meanwhile CLAUDE.md sits
in the cached prefix and is billed at ~10% after the first turn.

That is why this framework has **no dynamic rule-injection layer**, and why tools promising
"rules that load only when relevant" tend to cost more than the static file they replace. The
one place that trade genuinely pays is tool definitions, and Claude Code already does it
natively (deferred MCP schemas + tool search) with no hook required.

Corollary for hook authors: hooks may **append**, never rewrite or prune already-cached
history. Pruning per turn invalidates the cached prefix from that point on — the canonical
own-goal, and one Anthropic shipped itself (the 2026-04-23 postmortem, Bug 2: a
context-cleanup that was meant to run once ran every turn, producing cache misses *and* a
forgetful agent).

### Measure before you cut

Run `/context` in a clean session first. Two traps:

- **Context saved ≠ money saved.** Cached content bills at ~10%, so trimming a cached
  CLAUDE.md saves less than the raw token count suggests. It still buys quality — less noise,
  more room. Recurring uncached output (test logs, per-turn hook injections) is where the real
  spend is.
- **Verify against a current version.** Claude Code counted MCP instructions once *per tool*
  instead of once per server until January 2026, inflating those figures ~3x. Decisions made
  against that number were made against a ghost. The ground truth is
  `cache_read + cache_creation + input` from the API response.

---

## Core Layer

`core/` is entirely language-agnostic. Verification — the *executable* layer
never hardcodes a tool name (rules may cite tools as illustrative examples):

```bash
grep -rIE 'tsc|knip|eslint|firestore' core/hooks/scripts/
# Must return empty
```

### core/rules/

| File | Purpose |
|---|---|
| `operating-procedure.md` | Auto-router: triage by size (trivial → answer directly; substantial → apply sequence). Route-by-work-type table. |
| `ratchet-philosophy.md` | “The baseline is the floor” contract. Skip conditions every ratchet must implement. |
| `security-gates.md` | Canonical statement of the security gates. Correct hook types (secret-scan = PreToolUse, pre-push = blocking). |
| `commands-encode-workflows.md` | Commands are the implementation of auto-routing, not buttons humans press. |
| `close-protocol.md` | How every substantial turn must end: commit + status line, never push (enforced by close-guard + push policy). |
| `environment-canonical.md` | One true path per operation on this machine; `environment.forbiddenCommands` blocks the broken ones with the fix inline. |
| `incident-triage.md` | Triage protocol + living error dictionary: never re-derive a solved diagnosis. |
| `learning-loop.md` | Persistent memory that actually persists: project memory with index, post-run verification of headless automations. |
| `graphify.md` | Opt-in codebase-graph layer: consult the graph before crawling; imports ≠ runtime coupling; freshness + cost honesty. |

### core/commands/

| Command | Purpose |
|---|---|
| `/commit-checkpoint` | Run all configured gates, then commit safely. Reads manifest. Never `--amend`/`--no-verify`. |
| `/ci-simulate` | Run all `gates.prePush.steps` in order, report all failures (CI `if: always()` semantics). |
| `/typecheck` | Run `commands.typecheck` from manifest; report errors. |
| `/env-check` | Validate env vars documented in CLAUDE.md vs local env file. Never prints values. |
| `/graphify` | Build/query a tree-sitter knowledge graph (AST, zero tokens). explain/path/query for blast-radius, flow-tracing, orientation. Needs no `stack.json`. |

### core/hooks/

`core/hooks/settings.template.json` — copy to `.claude/settings.json`. Pre-wired:
- `PreToolUse` (Bash): `canonical-guard.py` (blocks `environment.forbiddenCommands` with the fix inline) + `pre-push-guard.py` (push policy + quality gate, blocking) + `secret-scan.sh` (blocking on commit) + `filter-verbose-guard.py` (non-blocking; collapses passing output per `context.filterVerbose`)
- `Stop`: `ratchet-guard.py` (dead-code ratchet, blocking, scope-by-diff via `CHANGED_FILES`) + `close-guard.py` (close protocol, reminds once)

`core/hooks/scripts/read-config.py` — the manifest reader. Takes a dotted key path
(e.g. `commands.typecheck`), walks up the directory tree to find `stack.json`, returns
the value (JSON for arrays/objects). Missing key → exit 1 = safe skip for callers.

---

## ExampleApp Reference Example

`examples/nextjs-firebase/` is an **anonymized mirror** of the `.claude/` directory running in
production in a real SaaS (TypeScript/Next.js 15/Firebase/Vercel) — file-for-file identical,
with company/client/person names replaced by generic placeholders.
Use it as the definitive reference for a fully-adopted setup. To refresh it from the source
project: `python scripts/sync-example.py <project-root> examples/nextjs-firebase`
(the `sync-manifest.json` carries the file map, sanitization rules and a leak check).

### Contents

| Path | Description |
|---|---|
| `stack.json` | Fully-filled manifest: 8 commands, sentrux as structural ratchet, design + cron-doc gates, `push: operator-only`, `closeProtocol: blocking`, 4 `forbiddenCommands` |
| `settings.json` | Production `.claude/settings.json`: 3 blocking `PreToolUse` hooks, 6 advisory `PostToolUse` hooks, 4 blocking `Stop` hooks |
| `rules/` | 12 domain rules (anonymized from production) |
| `commands/` | 15 slash commands (anonymized from production) |
| `ast-rules/` | TypeScript ast-grep rules — optional structural enforcement add-on |
| `scripts/` | 13 production scripts (guards, baseline checkers, secret scan, dev-up) |
| `sync-manifest.json` | File map + sanitization rules for `scripts/sync-example.py` |

### Rules (13)

| Rule | Domain |
|---|---|
| `alert-engine-pattern.md` | Pure-computation contract: no DB/network in `evaluate()` |
| `ci-zero-failure.md` | What CI checks, where each check lives, SKIP_PREPUSH rules |
| `code-quality-ratchets.md` | any-type ratchet, large files (>800 lines), dead-code, design contract |
| `console-error-pattern.md` | `console.error` prohibited in lib/api; `reportError()` for runtime errors |
| `cron-security.md` | `validateCronSecret()` first, `withErrorReporting()` wrap, idempotency, maxDuration |
| `firestore-conventions.md` | 4 doc ID patterns, ignoreUndefinedProperties, index drift prevention |
| `folder-organization.md` | scripts/ subcategories, import path conventions |
| `operating-procedure.md` | App-specific routing (alert engines, cron, channel_snapshots, ARS currency) + close protocol |
| `regional-thresholds.md` | ARS vs USD scale differences for ROAS/CPA/spend thresholds |
| `windows-environment.md` | Canonical vs forbidden path per operation on the dev machine (lint, DB access, shell dialects) |
| `ui-delivery-checklist.md` | Deterministic UI-delivery checklist (nav wiring, empty states, mirrors) + canonical smoke-test recipe |
| `incident-triage.md` | Triage protocol + 11-row living dictionary of known errors (cause → fix) |
| `graphify.md` | Real graphify wiring: `python -m graphify` (Windows shim), root-scoped graph, 3 hooks, imports-only blind spot |

### Commands (15)

| Command | Purpose |
|---|---|
| `/ts-check` | Run `tsc --noEmit`, report errors |
| `/test-alerts` | Run alert engine unit tests, map failures to engine files |
| `/commit-checkpoint` | ESLint auto-fix + tsc + tests + any-ratchet + commit safely |
| `/ci-simulate` | Run all 6 CI steps in order, report all failures at once |
| `/new-alert` | Scaffold new alert type (engine, test, docs, wiring) |
| `/new-channel-sync` | Scaffold new channel integration (service, cron, OAuth, types) |
| `/env-check` | Validate env vars vs `.env.local` |
| `/deploy-indexes` | Diff local vs deployed Firestore indexes, deploy safely |
| `/audit-parity` | Data drift detection between stored snapshots and live API |
| `/client-health` | Per-client health snapshot (data freshness, alerts, cron failures) |
| `/slack-preview` | Preview a Slack digest dry-run without posting |
| `/backfill-client` | Data backfill with dry-run safety and budget tracking |
| `/prompt-version` | AI Analyst system prompt versioning (staging → production) |
| `/design-gate` | Enforce design-contract ratchet on UI changes |
| `/fix-any` | Replace `any` types in a file with typed alternatives |

### Hooks (settings.json — 13 total)

| Event | Hook | Blocking? |
|---|---|---|
| `PreToolUse` (Bash) | `pre-bash-canonical-guard.py` (commands that always fail on this machine) | ✅ Yes (exit 2, fix inline) |
| `PreToolUse` (Bash `git push`) | `pre-push-quality-guard.py` (push interceptor + quality gate) | ✅ Yes (exit 2) |
| `PreToolUse` (Bash `git commit`) | `check-no-secrets.sh` | ✅ Yes (exit 1) |
| `PostToolUse` (Edit/Write) | File-type reminders (alert engine / cron / indexes / service) | Advisory |
| `PostToolUse` (Edit/Write) | `check-error-reporting.js` (API routes) | Advisory |
| `PostToolUse` (Edit/Write) | `check-no-new-any.js` (any-type ratchet) | Advisory |
| `PostToolUse` (Edit/Write) | `check-cron-doc-sync.js` (crons.yml sync) | Advisory |
| `PostToolUse` (Edit/Write) | `use-client` directive check (React hooks) | Advisory |
| `PostToolUse` (Edit/Write) | Critical utility change reminder | Advisory |
| `Stop` | `stop-ui-smoke-guard.py` (UI touched without a browser smoke test) | ✅ Yes (exit 2, once) |
| `Stop` | `stop-dead-code-guard.py` (dead-code ratchet, scope-by-diff) | ✅ Yes (exit 2) |
| `Stop` | `stop-design-guard.py` (design-contract ratchet, scope-by-diff) | ✅ Yes (exit 2) |
| `Stop` | `stop-dirty-tree-guard.py` (close protocol: uncommitted code) | ✅ Yes (exit 2, once) |

The three `PreToolUse` hooks are **blocking**. The `Stop` hooks exit 2 to force cleanup
before Claude ends a turn; the smoke and dirty-tree guards block only once per close
(`stop_hook_active` breaks the loop), and the two ratchet guards pass `CHANGED_FILES`
so inherited debt from other sessions downgrades to a warning.

---

## Adopting This Framework

See [docs/adoption.md](docs/adoption.md) for the full step-by-step guide.

Short version:

```bash
# 1. Copy the universal core
cp -r core/ your-project/.claude/core/

# 2. Copy the settings template
cp core/hooks/settings.template.json your-project/.claude/settings.json

# 3. Write your stack.json at the project root
cp stack.example.json your-project/stack.json
# fill in: commands.typecheck, commands.lint, commands.test, security.secretScan, gates.prePush.steps

# 4. Create CLAUDE.md from the template
cp core/CLAUDE.template.md your-project/.claude/CLAUDE.md
# fill {{placeholders}}

# 5. Freeze baselines (one-time)
# run your dead-code tool with --write, commit the baseline file
```

No language-specific code edits needed in `core/`. The framework adapts entirely through `stack.json`.
