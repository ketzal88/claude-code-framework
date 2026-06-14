# Spec: Claude Code Framework — Agnostic, Config-Driven Rewrite

**Date:** 2026-06-13
**Status:** Design approved, pending spec review
**Author:** Gabriel + Claude

---

## 1. Problem & Context

`ketzal88/claude-code-framework` started as the documented Claude Code setup for **Worker Brain**, a production Next.js 14 + Firebase + TypeScript SaaS. It has real value — a layered enforcement system (rules → commands → AST → hooks → ratchets), an auto-routing operating procedure, blocking security/quality gates — but it has **two problems**:

1. **It is technology-coupled.** Everything assumes TypeScript / Next.js / Firebase: `tsc`, `eslint`, `knip`, ast-grep TS patterns, Firestore conventions, commands like `/ts-check` and `/deploy-indexes`. A Java, Python, or Go project cannot adopt it without rewriting the internals.

2. **It has drifted from the real setup.** The published repo is a hand-generalized *snapshot* that is now stale and partial versus the `.claude/` directory actually running in the Worker Brain repo (the one that "works great"). Concrete evidence:
   - Published rules: `pure-engine-pattern`, `error-reporting-pattern`, `optional-fields-migration`, `ci-zero-failure`, `code-quality-ratchets`, `cron-security`, `operating-procedure`.
   - Real ai-analyzer rules: `alert-engine-pattern`, `console-error-pattern`, `firestore-conventions`, `regional-thresholds`, `folder-organization`, `cron-security`, `operating-procedure`, `code-quality-ratchets`, `ci-zero-failure`.
   - Published commands: 6. Real commands: ~16.
   - `sentrux` (SAST via MCP), the blocking pre-push guard mirroring CI's 6 checks, and several hooks exist in reality but are absent or misdescribed in the framework (e.g. the README calls the pre-push gate "advisory" when it is **blocking**).

**The user's goal, in their words:** *"lo importante es que como trabajamos en este repo que anda joya quede reflejado en este framework para llevar a otros repos."* — faithfully capture the real, working setup, then make it portable to other repos and languages.

So this rewrite has **two dimensions**:

- **Fidelity** — the framework must honestly reflect what actually runs in Worker Brain today.
- **Agnosticism** — that captured setup must become portable to any language via configuration, not code edits.

---

## 2. Goals / Non-Goals

### Goals
- A **universal core** (`core/`) that is 100% language-agnostic.
- A single **manifest** (`stack.json`) per project that declares language + tool commands; universal hooks/commands read it instead of hardcoding `tsc`/`knip`/etc.
- A first-class, named **Security Layer** (secret-scan, blocking pre-push gate, SAST, dep-audit) — resolving the "are the security gates here?" gap and giving `sentrux` a real home as the recommended SAST adapter.
- `examples/worker-brain/` as a **faithful, current mirror** of the real `.claude/` setup, with a fully-filled `stack.json` — the proof the framework reflects a setup that works.
- A community-facing, language-neutral **README** + `docs/adoption.md`.
- Fix the documentation bugs discovered (notably the "advisory" vs "blocking" pre-push description).

### Non-Goals
- No `profiles/<language>/` tree. The user explicitly chose **config-driven via a single manifest** over a profiles tree.
- No interactive `init` generator (rejected in favor of "copy core + write manifest").
- Not porting the domain-specific AST rules to other languages — language-specific structural rules are documented as an *optional, bring-your-own* add-on, not part of the core.
- Not building a second worked example in another language now (the user chose "one reference example").

---

## 3. Architecture

```
Universal gate  ──reads──►  stack.json  ──runs──►  the command for THIS language
(secret-scan,               (declares test,        (tsc / mvn test / pytest / go test)
 pre-push, ratchets,         lint, sast,
 SAST, dep-audit)            ratchet tools…)
```

Three layers:

1. **`core/`** — language-agnostic. Rules (philosophy + invariants), command templates, hook scripts, security layer. Parameterized only through the manifest.
2. **`stack.json`** — the per-project manifest. The *only* file an adopter must author. Declares language label, package manager, the command for each gate, security tools, ratchet tools, and path globs.
3. **`examples/worker-brain/`** — a faithful mirror of the real Worker Brain `.claude/` setup, including a complete `stack.json`. Domain rules, domain commands, and the TS ast-grep rules live here as a worked reference.

### 3.1 The manifest (`stack.json`)

Validated by `stack.schema.json`. Every key is optional; an **absent key means that gate is a safe no-op (skipped)**. This is the rule that keeps config-driven from becoming fragile magic.

```jsonc
{
  "language": "typescript",
  "packageManager": "npm",
  "commands": {
    "typecheck": "tsc --noEmit",        // java: "mvn -q compile" · py: "mypy ."
    "lint":      "npm run lint",         // java: "mvn checkstyle:check" · py: "ruff check"
    "test":      "npm run test:unit",    // java: "mvn test" · py: "pytest -q"
    "build":     "npm run build"
  },
  "security": {
    "secretScan": "core/security/secret-scan.sh",   // agnostic default, ships in core
    "sast":       "sentrux scan",                     // py: "bandit -r ." · multi: "semgrep --config auto"
    "depAudit":   "npm audit --audit-level=high"      // py: "pip-audit" · go: "govulncheck ./..."
  },
  "ratchets": {
    "deadCode":   "knip",                             // optional; py: "vulture", etc.
    "baselineDir": ".baselines/"
  },
  "gates": {
    "preCommit": { "secretScan": "blocking" },
    "prePush":   { "blocking": true, "steps": ["typecheck", "lint", "test", "sast"] }
  },
  "paths": { "source": ["src/**"], "codeExtensions": [".ts", ".tsx"] }
}
```

### 3.2 Repo layout (target)

```
claude-code-framework/
├─ README.md                 # community-facing, language-neutral
├─ stack.schema.json         # validates any stack.json
├─ stack.example.json        # blank template with comments
├─ core/                     # 100% AGNOSTIC
│  ├─ CLAUDE.template.md      # brain template; {{placeholders}} filled from manifest
│  ├─ rules/
│  │  ├─ operating-procedure.md      # auto-router (already agnostic; light edits)
│  │  ├─ ratchet-philosophy.md       # "the baseline is the floor" (generalizes dead-code/any/design)
│  │  ├─ security-gates.md           # NEW: universal security invariants
│  │  └─ commands-encode-workflows.md
│  ├─ commands/              # commit-checkpoint, ci-simulate, typecheck, env-check (read manifest)
│  ├─ hooks/
│  │  ├─ settings.template.json
│  │  └─ scripts/
│  │     ├─ read-config.(sh|py)   # the manifest reader, shared by every gate
│  │     ├─ secret-scan.sh         # agnostic regex secret scanner
│  │     ├─ pre-push-guard.py      # reads gates.prePush.steps; BLOCKING
│  │     ├─ ratchet-guard.py       # generic baseline ratchet
│  │     └─ sast-scan.sh           # runs security.sast
│  └─ security/
│     ├─ secret-patterns.txt       # PEM/AWS/Slack/Anthropic/OpenAI/Meta/etc.
│     └─ README.md                 # how to plug sentrux / semgrep / bandit / gosec
├─ examples/
│  └─ worker-brain/          # faithful mirror of the REAL .claude/ (the "anda joya" reference)
│     ├─ stack.json           # fully-filled TS/Next/Firebase manifest
│     ├─ rules/               # firestore-conventions, alert-engine-pattern, cron-security,
│     │                       #   console-error-pattern, regional-thresholds, folder-organization
│     ├─ commands/            # ts-check, test-alerts, deploy-indexes, audit-parity, fix-any, …
│     └─ ast-rules/           # the ast-grep TS rules (optional add-on demo)
└─ docs/
   └─ adoption.md            # copy core/, write your stack.json, done
```

---

## 4. Security Layer (first-class)

A named layer rather than scattered hooks. Directly answers the user's question "are the security gates in the framework?".

| Gate | Implementation | Agnostic? | Blocking? |
|---|---|---|---|
| **secret-scan** | `core/security/secret-scan.sh` + `secret-patterns.txt` | ✅ Total (regex over text) | ✅ pre-commit |
| **pre-push gate** | `pre-push-guard.py` reads `gates.prePush.steps`, runs each `commands[step]` | ✅ Skeleton universal; commands from manifest | ✅ (README bug fixed) |
| **SAST** | `sast-scan.sh` runs `security.sast` | ✅ Gate universal; tool is the adapter | configurable |
| **dep-audit** | runs `security.depAudit` | ✅ universal; per-language command | configurable |

- `sentrux` becomes the **recommended SAST adapter** in the worker-brain example (wired through `security.sast`), with `semgrep` / `bandit` / `gosec` documented as alternatives in `core/security/README.md`.
- The agnostic `secret-scan.sh` is the existing `check-no-secrets.sh` generalized (filename checks + staged-diff pattern checks).
- The blocking pre-push guard generalizes `pre-push-quality-guard.py`: instead of hardcoding the 6 CI steps, it iterates `gates.prePush.steps` and runs the manifest command for each. Bypass `SKIP_PREPUSH=1` preserved.

---

## 5. The read-config mechanism (the one delicate piece)

`read-config` is a small, dependency-light reader (`jq` when available, Python fallback — Python is always present). Contract:

- `read-config <dotted.key>` → prints the resolved value (e.g. `read-config commands.typecheck` → `tsc --noEmit`).
- Missing key → empty output + non-zero exit, so callers treat the gate as a **safe skip**, never an error.
- Under ~30 lines, no surprising behavior. This is the heart of config-driven; it must be boringly reliable.

Every hook and command becomes a thin manifest-reader: it asks `read-config` for the command, runs it, reports. No tool name is hardcoded anywhere in `core/`.

---

## 6. Fidelity step (capturing the real setup)

Before/while extracting the agnostic core, reconcile the framework with the **actual** Worker Brain `.claude/` (source of truth: `c:\Users\gabri\Documents\Worker\Webs\ai-analyzer\.claude\` + `scripts/`):

- Bring `examples/worker-brain/rules/` to the real, current rule set (not the stale generalized names).
- Bring `examples/worker-brain/commands/` to the real ~16 commands.
- Reflect the real hooks (blocking secret-scan, blocking pre-push mirroring CI, dead-code + design Stop ratchets, doc-sync, use-client check, any-ratchet, error-reporting check).
- Record `sentrux` as the real SAST tool in the example manifest.
- Fix every doc statement that misrepresents reality (advisory vs blocking, hook count, command count).

`examples/worker-brain/` is the regression test for fidelity: if it diverges from the real `.claude/`, the framework is lying.

---

## 7. Migration plan (phased)

The published repo is now cloned at `c:\tmp\framework-update\repo`.

1. **Carve layers** — split current `examples/.claude/` into `core/` (universal) and `examples/worker-brain/` (domain). Mostly file moves + renames.
2. **Author the manifest** — `stack.schema.json`, `stack.example.json`, and the worker-brain `stack.json` filled from reality.
3. **Generalize scripts** — rewrite `secret-scan.sh`, `pre-push-guard.py`, `ratchet-guard.py`, `sast-scan.sh` to read the manifest via `read-config`; remove hardcoded TS tool names from `core/`.
4. **Rewrite hooks** — `core/hooks/settings.template.json` wired to the generic scripts; reminders parameterized by `paths`.
5. **Security layer** — assemble `core/security/` (patterns + adapter README), wire `sentrux` in the example.
6. **Rewrite README** — language-neutral; add Security Layer section + SAST adapter table; fix the advisory/blocking bug; document the manifest and adoption flow.
7. **Adoption doc** — `docs/adoption.md`: copy `core/`, write `stack.json`, done.

Each phase is independently reviewable. No phase ships a `core/` file that names a language-specific tool.

---

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| `read-config` becomes fragile/magic | Keep it <30 lines, missing-key = safe skip, ship unit tests against a fixture manifest |
| Cross-platform shell (Windows/bash) | Hooks already use Python one-liners; keep Python as the portable layer, `jq` optional |
| Example drifts from real setup again | Treat `examples/worker-brain/` as a mirror with a documented source-of-truth path; future updates sync from ai-analyzer |
| Over-abstraction hurts readability | Manifest swaps **commands only**; structural/language-specific content stays out of core, documented as opt-in |

---

## 9. Success criteria

1. A Java/Python/Go project can adopt the framework by copying `core/` and writing a `stack.json` — zero edits to hooks or commands.
2. `core/` contains **no** hardcoded language-specific tool name (`tsc`, `knip`, `firestore`, etc.).
3. The Security Layer runs secret-scan (blocking), pre-push (blocking), and SAST driven entirely by the manifest.
4. `examples/worker-brain/stack.json` + rules + commands faithfully reflect the real `.claude/` setup that runs today.
5. README is language-neutral, documents the manifest + adoption + security layer, and contains no statement contradicted by reality.
