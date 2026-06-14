# Claude Code Framework — language-agnostic, config-driven

> A portable Claude Code setup that enforces code quality and security **regardless of language**.
> You copy a universal `core/`, write a single `stack.json` declaring your toolchain, and the
> rules, commands, hooks, ratchets, and security gates run against **your** stack — Java, Python,
> Go, TypeScript, Rust, whatever — with zero edits to the framework internals.

Derived from a production Next.js 14 + Firebase + TypeScript SaaS (see [`examples/worker-brain/`](examples/worker-brain/)),
then made tech-agnostic so the same discipline travels to any repo.

---

## Philosophy

1. **Teach, don't repeat.** Every correction becomes a rule in a file, so it never happens again.
2. **Automate the guardrails.** Hooks run on every edit/commit/push — Claude can't forget to check.
3. **The baseline is the floor.** Quality ratchets (dead-code, design, structural regression) can only go down, never up.
4. **Commands encode workflows.** Multi-step processes become one-line slash commands.
5. **One manifest, any language.** Tool names live in `stack.json`, never hardcoded in the framework.

---

## How it's agnostic: the manifest

The whole framework is parameterized by one file. Universal gates **read** `stack.json` and run the
command for **your** language. An absent key means that gate is skipped — a safe no-op, never an error.

```jsonc
{
  "language": "typescript",
  "packageManager": "npm",
  "commands": {
    "typecheck": "tsc --noEmit",        // java: "mvn -q compile"  · py: "mypy ."        · go: "go vet ./..."
    "lint":      "npm run lint",         // java: "mvn checkstyle:check" · py: "ruff check" · go: "golangci-lint run"
    "test":      "npm run test:unit",    // java: "mvn test"        · py: "pytest -q"     · go: "go test ./..."
    "build":     "npm run build"
  },
  "security": {
    "secretScan": "core/hooks/scripts/secret-scan.sh",  // agnostic default, ships in core
    "sast":       "",                                     // optional one-shot: "semgrep --config auto" · py: "bandit -r ." · go: "gosec ./..."
    "depAudit":   "npm audit --audit-level=high"          // py: "pip-audit" · go: "govulncheck ./..." · java: "mvn dependency-check:check"
  },
  "ratchets": {
    "deadCode":   "knip",                                 // py: "vulture ." — optional, baseline-diffed
    "structural": "sentrux gate",                         // opt-in structural-regression ratchet vs baseline
    "baselineDir": ".sentrux/"
  },
  "gates": {
    "preCommit": { "secretScan": "blocking" },
    "prePush":   { "blocking": true, "steps": ["typecheck", "lint", "test", "structural"] }
  },
  "paths": { "source": ["src/**"], "codeExtensions": [".ts", ".tsx"] }
}
```

> `stack.json` is **plain JSON** — the `//` comments above are illustrative only. Start from
> [`stack.example.json`](stack.example.json); the schema is [`stack.schema.json`](stack.schema.json).

The reader is one tiny script — [`core/hooks/scripts/read-config.py`](core/hooks/scripts/read-config.py)
(~50 lines, no deps): `read-config commands.typecheck` → prints the command, or exits non-zero so the
caller skips the gate. Nothing else in `core/` knows what language you use.

---

## Repository layout

```
core/                      # 100% language-agnostic — copy this into your project
├─ CLAUDE.template.md        # brain template; fill the <!-- fill me --> block once, by hand
├─ rules/                    # operating-procedure, ratchet-philosophy, security-gates, …
├─ commands/                 # commit-checkpoint, ci-simulate, typecheck, env-check (all read the manifest)
├─ hooks/
│  ├─ settings.template.json # wire these into your .claude/settings.json
│  └─ scripts/               # read-config, secret-scan, pre-push-guard, ratchet-guard, sast-scan
└─ security/                 # secret-patterns.txt + adapter guide (sentrux / semgrep / bandit / gosec)

stack.schema.json           # validates any stack.json
stack.example.json          # blank manifest to copy

examples/
└─ worker-brain/            # a real, working setup (TS/Next/Firebase) — the proof, with a filled stack.json

docs/adoption.md            # step-by-step adoption guide
```

---

## The enforcement pyramid

```
        ┌──────────┐
        │  Hooks   │  ← automatic, every action (some blocking)
        ├──────────┤
        │ Ratchets │  ← baseline-is-the-floor (dead-code, design, structural)
        ├──────────┤
        │ Commands │  ← user/AI-invoked workflows (/commit-checkpoint, /ci-simulate)
        ├──────────┤
        │  Rules   │  ← always-loaded invariants (.md)
        ├──────────┤
        │CLAUDE.md │  ← architecture + reference
        └──────────┘
```

Each layer reinforces the ones below it. Commands and hooks resolve their actual commands from
`stack.json`, so the same pyramid works in any language.

---

## Security Layer

A first-class, named layer — not scattered hooks. Every project, in every language, wants the same
guarantees; only the *tool* differs (that's the adapter, declared in `stack.json`).

| Gate | What it does | Driven by | Blocking? |
|---|---|---|---|
| **secret-scan** | Blocks commits that stage secret files or known key patterns (regex over the staged diff). 100% language-agnostic. | `security.secretScan` (ships in `core/`) | ✅ **pre-commit** |
| **pre-push gate** | Runs every step in `gates.prePush.steps` (each resolved from `commands.*` or `ratchets.*`), mirrors CI, all steps run even if one fails. | `gates.prePush.steps` | ✅ **pre-push** |
| **structural ratchet** | Opt-in structural-regression check vs a committed baseline — skips silently if the tool/baseline isn't present. | `ratchets.structural` (e.g. `sentrux gate`) | ✅ as a pre-push step |
| **SAST (optional)** | One-shot static analysis when you want it. | `security.sast` | configurable |
| **dep-audit (optional)** | Dependency vulnerability scan. | `security.depAudit` | configurable |

### SAST / structural adapters

| Stack | structural ratchet | one-shot SAST | dep-audit |
|---|---|---|---|
| Any | `sentrux gate` (baseline-diffed) | `semgrep --config auto` | — |
| TypeScript/JS | — | `semgrep` | `npm audit --audit-level=high` |
| Python | — | `bandit -r .` | `pip-audit` |
| Go | — | `gosec ./...` | `govulncheck ./...` |
| Java | — | `spotbugs` | `mvn dependency-check:check` |

> **`sentrux` is a structural-regression ratchet, not a one-shot SAST.** It runs as a pre-push step
> (`sentrux gate <root>` diffed against a baseline in `ratchets.baselineDir`), opt-in via the
> `SENTRUX_BIN` env var, and **skips silently** when the binary or baseline is absent. It belongs to
> the ratchet family (same "baseline is the floor" semantics as dead-code/design), which is why it's
> modeled under `ratchets.structural` and listed in `gates.prePush.steps` — *not* under `security.sast`.

---

## Adoption (3 steps)

1. **Copy `core/`** into your repo (e.g. as `.claude-framework/` or merge into your `.claude/`).
2. **Write `stack.json`** — copy `stack.example.json`, fill ~6–8 commands for your toolchain.
3. **Wire the hooks** — merge `core/hooks/settings.template.json` into your `.claude/settings.json`.

That's it. secret-scan, the blocking pre-push gate, ratchets, and any SAST you declared now run with
**your** tools. Full walkthrough in [`docs/adoption.md`](docs/adoption.md).

---

## Worked example

[`examples/worker-brain/`](examples/worker-brain/) is a real production setup (Next.js 14 + Firebase +
TypeScript) with a fully-filled [`stack.json`](examples/worker-brain/stack.json): 9 rules, 15 commands,
6 ast-grep structural rules, blocking secret-scan + pre-push gates, dead-code + design Stop-hook
ratchets, and the `sentrux` structural ratchet. It's the proof the framework reflects a setup that
actually works — read it to see how every manifest key maps to a real gate.

---

## Notes for adopters

- **Hooks are Python one-liners** that parse the tool-event JSON on stdin. Python is the portable
  layer (works on Windows/macOS/Linux); `jq` is used only when available.
- **Advisory hooks** write to `stderr` (visible to Claude, non-blocking). **Blocking hooks** exit
  non-zero. The secret-scan is a **`PreToolUse`** hook on `git commit` — it must run *before* the
  commit, because afterwards `git diff --cached` is empty and nothing would be caught.
- **The pre-push gate is blocking**, not advisory — it exits non-zero and stops the push on any
  failed step. Docs-only bypass: `SKIP_PREPUSH=1` (allowed only when every changed file matches the
  CI paths-ignore set).
- **Ratchets only ever lower the floor.** When you genuinely clean up and the count drops, regenerate
  the baseline; the gate blocks any regression above it.
