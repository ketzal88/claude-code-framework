# Claude Code Framework — Language-Agnostic, Config-Driven

A layered enforcement system for Claude Code that works with **any language or framework**.
Three layers: a universal `core/` that reads a per-project `stack.json` manifest, a reference
example for TypeScript/Next.js/Firebase ([Worker Brain](examples/worker-brain/)), and a security
layer (secret-scan, blocking pre-push gate, SAST, dep-audit) driven entirely by the manifest.

---

## Table of Contents

1. [Philosophy](#philosophy)
2. [Architecture](#architecture)
3. [stack.json — The Manifest](#stackjson--the-manifest)
4. [Security Layer](#security-layer)
5. [Core Layer](#core-layer)
6. [Worker Brain Reference Example](#worker-brain-reference-example)
7. [Adopting This Framework](#adopting-this-framework)

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
| **Reference** | `examples/worker-brain/` | Faithful mirror of a real production TypeScript/Next.js/Firebase setup. |

### Repository Structure

```
claude-code-framework/
├─ README.md
├─ stack.schema.json          # validates any stack.json
├─ stack.example.json         # blank template
├─ core/
│  ├─ CLAUDE.template.md      # brain template with {{placeholders}}
│  ├─ rules/
│  │  ├─ operating-procedure.md
│  │  ├─ ratchet-philosophy.md
│  │  ├─ security-gates.md
│  │  └─ commands-encode-workflows.md
│  ├─ commands/
│  │  ├─ commit-checkpoint.md
│  │  ├─ ci-simulate.md
│  │  ├─ typecheck.md
│  └─ hooks/
│     ├─ settings.template.json
│     └─ scripts/
│        ├─ read-config.py       # manifest reader — heart of config-driven
│        ├─ secret-scan.sh       # agnostic regex secret scanner
│        ├─ pre-push-guard.py    # reads gates.prePush.steps; BLOCKING
│        ├─ ratchet-guard.py     # generic baseline ratchet (Stop hook)
│        └─ sast-scan.sh         # runs security.sast
├─ core/security/
│  ├─ secret-patterns.txt
│  └─ README.md               # SAST adapter docs
└─ examples/
   └─ worker-brain/
      ├─ stack.json             # fully-filled TypeScript/Next.js/Firebase manifest
      ├─ settings.json          # real .claude/settings.json (verbatim)
      ├─ rules/                 # 9 domain rules (verbatim from production)
      ├─ commands/              # 15 slash commands (verbatim from production)
      ├─ ast-rules/             # optional TypeScript ast-grep rules
      └─ scripts/               # 4 production scripts
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
    "prePush":   { "blocking": true, "steps": ["typecheck", "lint", "test"] }
  },
  "paths": {
    "source": ["src/**"],
    "codeExtensions": [".ts", ".tsx"]
  }
}
```

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

Four gates, driven entirely by `stack.json`. None are hardcoded — all adapt via the manifest.

| Gate | Hook Type | Blocking? | Manifest Key |
|---|---|---|---|
| **Secret scan** | `PreToolUse` (Bash `git commit`) | ✅ Yes — blocks the commit | `security.secretScan` |
| **Pre-push quality gate** | `PreToolUse` (Bash `git push`) | ✅ Yes — blocks the push | `gates.prePush.steps` |
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

[sentrux](https://github.com/ketzal88/sentrux) is a **structural-regression ratchet**, not a SAST
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

## Core Layer

`core/` is entirely language-agnostic. Verification:

```bash
grep -rIE 'tsc|knip|eslint|firestore' core/
# Must return empty
```

### core/rules/

| File | Purpose |
|---|---|
| `operating-procedure.md` | Auto-router: triage by size (trivial → answer directly; substantial → apply sequence). Route-by-work-type table. |
| `ratchet-philosophy.md` | “The baseline is the floor” contract. Skip conditions every ratchet must implement. |
| `security-gates.md` | Canonical statement of all four security gates. Correct hook types (secret-scan = PreToolUse, pre-push = blocking). |
| `commands-encode-workflows.md` | Commands are the implementation of auto-routing, not buttons humans press. |

### core/commands/

| Command | Purpose |
|---|---|
| `/commit-checkpoint` | Run all configured gates, then commit safely. Reads manifest. Never `--amend`/`--no-verify`. |
| `/ci-simulate` | Run all `gates.prePush.steps` in order, report all failures (CI `if: always()` semantics). |
| `/typecheck` | Run `commands.typecheck` from manifest; report errors. |
| `/env-check` | Validate env vars documented in CLAUDE.md vs local env file. Never prints values. |

### core/hooks/

`core/hooks/settings.template.json` — copy to `.claude/settings.json`. Pre-wired:
- `PreToolUse` (Bash): `pre-push-guard.py` (blocking) + `secret-scan.sh` (blocking on commit)
- `Stop`: `ratchet-guard.py` (dead-code ratchet, blocking)

`core/hooks/scripts/read-config.py` — the manifest reader. Takes a dotted key path
(e.g. `commands.typecheck`), walks up the directory tree to find `stack.json`, returns
the value (JSON for arrays/objects). Missing key → exit 1 = safe skip for callers.

---

## Worker Brain Reference Example

`examples/worker-brain/` is a **verbatim mirror** of the `.claude/` directory running in
production in the Worker Brain SaaS (TypeScript/Next.js 14/Firebase/Vercel).
Use it as the definitive reference for a fully-adopted setup.

### Contents

| Path | Description |
|---|---|
| `stack.json` | Fully-filled manifest: 8 commands, sentrux as structural ratchet, design + cron-doc gates |
| `settings.json` | Real `.claude/settings.json`: 2 blocking `PreToolUse` hooks, 6 advisory `PostToolUse` hooks, 2 blocking `Stop` hooks |
| `rules/` | 9 domain rules (verbatim from production) |
| `commands/` | 15 slash commands (verbatim from production) |
| `ast-rules/` | TypeScript ast-grep rules — optional structural enforcement add-on |
| `scripts/` | 4 production scripts (pre-push guard, dead-code ratchet, secret scan) |

### Rules (9)

| Rule | Domain |
|---|---|
| `alert-engine-pattern.md` | Pure-computation contract: no DB/network in `evaluate()` |
| `ci-zero-failure.md` | What CI checks, where each check lives, SKIP_PREPUSH rules |
| `code-quality-ratchets.md` | any-type ratchet, large files (>800 lines), dead-code, design contract |
| `console-error-pattern.md` | `console.error` prohibited in lib/api; `reportError()` for runtime errors |
| `cron-security.md` | `validateCronSecret()` first, `withErrorReporting()` wrap, idempotency, maxDuration |
| `firestore-conventions.md` | 4 doc ID patterns, ignoreUndefinedProperties, index drift prevention |
| `folder-organization.md` | scripts/ subcategories, import path conventions |
| `operating-procedure.md` | WB-specific routing (alert engines, cron, channel_snapshots, ARS currency) |
| `regional-thresholds.md` | ARS vs USD scale differences for ROAS/CPA/spend thresholds |

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

### Hooks (settings.json — 10 total)

| Event | Hook | Blocking? |
|---|---|---|
| `PreToolUse` (Bash `git push`) | `pre-push-quality-guard.py` | ✅ Yes (exit 2) |
| `PreToolUse` (Bash `git commit`) | `check-no-secrets.sh` | ✅ Yes (exit 1) |
| `PostToolUse` (Edit/Write) | File-type reminders (alert engine / cron / indexes / service) | Advisory |
| `PostToolUse` (Edit/Write) | `check-error-reporting.js` (API routes) | Advisory |
| `PostToolUse` (Edit/Write) | `check-no-new-any.js` (any-type ratchet) | Advisory |
| `PostToolUse` (Edit/Write) | `check-cron-doc-sync.js` (crons.yml sync) | Advisory |
| `PostToolUse` (Edit/Write) | `use-client` directive check (React hooks) | Advisory |
| `PostToolUse` (Edit/Write) | Critical utility change reminder | Advisory |
| `Stop` | `stop-dead-code-guard.py` (dead-code ratchet) | ✅ Yes (exit 2) |
| `Stop` | `stop-design-guard.py` (design-contract ratchet) | ✅ Yes (exit 2) |

Both `PreToolUse` hooks are **blocking**: the pre-push guard exits 2 to abort the push;
the secret scan exits 1 to abort the commit. Both `Stop` hooks exit 2 to force cleanup
before Claude ends a turn.

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
