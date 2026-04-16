# Claude Code Setup Guide — Worker Brain

> How we configured Claude Code for a production Next.js 14 + Firebase + Vercel SaaS.
> 12 slash commands, 7 diagnostic subagents, 6 AST rules, 5 automated hooks, 14 development workflow skills.
> Zero TS errors policy, pure-computation engines, TDD discipline, and a commit-checkpoint workflow that blocks regressions.

---

## Table of Contents

1. [Philosophy](#philosophy)
2. [Directory Structure](#directory-structure)
3. [CLAUDE.md — The Brain](#claudemd--the-brain)
4. [Rules (`.claude/rules/`)](#rules)
5. [Slash Commands (`.claude/commands/`)](#slash-commands)
6. [Hooks (`.claude/settings.json`)](#hooks)
7. [Subagents](#subagents)
8. [Skills](#skills)
9. [AST Rules (Static Analysis)](#ast-rules)
10. [How It All Connects](#how-it-all-connects)
11. [Plugins & Development Workflow Skills](#plugins--development-workflow-skills)
12. [Adapting This for Your Project](#adapting-this-for-your-project)

---

## Philosophy

Four principles drive this setup:

1. **Teach, don't repeat.** Rules go in files, not in your head. Every time you correct Claude, turn the correction into a rule so it never happens again.
2. **Automate the guardrails.** Hooks run automatically on every edit/commit/push — Claude can't forget to check.
3. **Pure functions are testable functions.** Any business logic engine must be pure computation (no DB access, no `new Date()`) — receives all data via input, returns results.
4. **Commands encode workflows.** Multi-step processes (safe commit, new alert scaffolding, index deploy) become one-line slash commands.

---

## Directory Structure

```
.claude/
├── CLAUDE.md                          # Main brain — architecture, patterns, reference tables
├── settings.json                      # Hooks (auto-run on edit/commit/push)
├── rules/
│   ├── alert-engine-pattern.md        # Pure-computation contract for engines
│   ├── cron-security.md               # Auth + error handling for crons
│   └── firestore-conventions.md       # Doc IDs, batching, index rules
├── commands/
│   ├── ts-check.md                    # /ts-check — TypeScript verification
│   ├── test-alerts.md                 # /test-alerts — alert engine unit tests
│   ├── commit-checkpoint.md           # /commit-checkpoint — safe commit workflow
│   ├── new-alert.md                   # /new-alert — scaffold new alert type
│   ├── new-channel-sync.md            # /new-channel-sync — scaffold new integration
│   ├── env-check.md                   # /env-check — validate env vars
│   ├── deploy-indexes.md              # /deploy-indexes — safe Firestore index deploy
│   ├── audit-parity.md               # /audit-parity — data drift detection
│   ├── client-health.md              # /client-health — per-client health snapshot
│   ├── slack-preview.md              # /slack-preview — digest dry-run
│   ├── backfill-client.md            # /backfill-client — data backfill with safety
│   └── prompt-version.md            # /prompt-version — AI prompt versioning
└── skills/
    └── worker-ast-rules/              # AST-based static analysis rules
        ├── SKILL.md
        ├── sgconfig.yml
        ├── scan.sh
        └── rules/
            ├── no-firestore-in-evaluate.yml
            ├── cron-requires-auth.yml
            ├── cron-must-declare-maxDuration.yml
            ├── no-hardcoded-conversion-metric.yml
            ├── no-console-error-swallow.yml
            └── no-null-as-delete-sentinel.yml
```

---

## CLAUDE.md — The Brain

The main `CLAUDE.md` is the entry point Claude reads every conversation. It contains:

### What goes here
- **Stack and env vars** — so Claude knows the tech without asking
- **Database schema** — collection names, doc ID patterns, relationships
- **Architectural patterns** — the 5-6 core patterns everything follows
- **Reference tables** — alert types, cron schedule, navigation routes
- **Testing commands** — exact bash commands to run tests
- **Pointers to modular rules** — `@.claude/rules/alert-engine-pattern.md` syntax

### What does NOT go here
- Implementation details (that's in the code)
- Tutorials or explanations (Claude already knows TypeScript/Next.js)
- Things that change weekly (use memory for that)

### Key pattern: Modular Rules

Instead of a 500-line CLAUDE.md, we split domain rules into focused files:

```markdown
## Modular Rules

@.claude/rules/firestore-conventions.md
@.claude/rules/alert-engine-pattern.md
@.claude/rules/cron-security.md
```

The `@` syntax imports the file's content into CLAUDE.md context. Each rule file is self-contained and referenceable by hooks and commands.

---

## Rules

Rules define **invariants that must always hold**. They're the laws of the codebase.

### Rule 1: Alert Engine Pattern (`alert-engine-pattern.md`)

**Core contract:**
```ts
class SomeAlertEngine {
  static evaluate(input: AlertEvaluationInput): Alert[] {
    // zero DB access — all data is in `input`
    // zero network calls
    // zero time-dependence (referenceDate is injected)
  }
}
```

**Why:** Makes every engine unit-testable without mocks. Both the cron path and the snapshot path share the exact same logic.

**Enforced by:** AST rule `no-firestore-in-evaluate`, hook reminder on engine file edit, `/test-alerts` command.

### Rule 2: Cron Security (`cron-security.md`)

Four non-negotiable requirements:
1. `validateCronSecret()` as the FIRST call
2. `withErrorReporting()` wrapper
3. Idempotent operations (upserts, deterministic doc IDs)
4. Explicit `maxDuration` export

**Why:** Every cron route is public-routable on Vercel — there's no "internal only."

**Enforced by:** AST rules `cron-requires-auth` + `cron-must-declare-maxDuration`, hook reminder on cron file edit.

### Rule 3: Firestore Conventions (`firestore-conventions.md`)

- **Doc ID patterns**: 4 standard formats, never invent new ones
- **Initialization**: `ignoreUndefinedProperties: true` — undefined is stripped, null is stored
- **Sub-source detection**: always via `rawData.source`, never infer from clientId
- **Batch limits**: 500 per batch, `BulkWriter` for more
- **Indexes**: add BEFORE shipping — queries silently fail without them

**Enforced by:** AST rule `no-null-as-delete-sentinel`, hook reminder on service file edit.

---

## Slash Commands

Commands encode multi-step workflows into one-line invocations.

### Development Workflow

| Command | Purpose | Key Behavior |
|---------|---------|-------------|
| `/ts-check` | Run `tsc --noEmit` | Reports errors grouped by file, doesn't fix |
| `/test-alerts` | Run alert engine unit tests | Parses output, maps failures to engine files |
| `/commit-checkpoint` | Safe commit | Runs ts-check + test-alerts before allowing commit |

### Scaffolding

| Command | Purpose | Key Behavior |
|---------|---------|-------------|
| `/new-alert` | Scaffold new alert type | Creates engine method, test, docs row, wiring — leaves predicate as TODO |
| `/new-channel-sync` | Scaffold channel integration | Service, cron, OAuth, types, docs — full skeleton |

### Operations

| Command | Purpose | Key Behavior |
|---------|---------|-------------|
| `/env-check` | Validate env vars | Cross-references CLAUDE.md docs vs `.env.local`, never prints values |
| `/deploy-indexes` | Deploy Firestore indexes | Diffs local vs deployed, blocks on removed indexes |
| `/audit-parity` | Data drift detection | Compares stored snapshots vs live API — read-only |
| `/client-health` | Client health snapshot | Data freshness, alerts, cron failures — one screen |
| `/slack-preview` | Preview digest | Renders morning/weekly/monthly without posting |
| `/backfill-client` | Data backfill | Safety checks, dry-run support, budget tracking |
| `/prompt-version` | AI prompt versioning | Staging → production workflow with diff and token estimates |

### Command Anatomy

Every command is a markdown file with YAML frontmatter:

```markdown
---
description: One-line description shown in /help
argument-hint: [optional] [--flags] <required>
---

Context for Claude about what this command does.

Steps:
1. Specific step with exact bash command
2. Parse and report
3. Safety checks

Never <thing that would be dangerous>.
```

**Design principles:**
- Commands are **diagnostic by default** — they report, they don't fix (unless explicitly asked)
- Safety rails are built in — `/commit-checkpoint` blocks on test failures, `/deploy-indexes` blocks on index removal
- Each command references the rules it enforces

---

## Hooks

Hooks run automatically via `.claude/settings.json`. They fire on specific tool events.

### Hook 1: File Change Reminders (PostToolUse on Edit/Write)

When Claude edits a file, context-aware reminders appear:

| File Pattern | Reminder |
|---|---|
| `src/lib/alert-engines/*.ts` | "Run /test-alerts before committing" |
| `/api/cron/**/route.ts` | "Verify validateCronSecret() + withErrorReporting()" |
| `firestore.indexes.json` | "Use /deploy-indexes to diff before deploying" |
| `*-service.ts` in `src/lib/` | "Consider running /audit-parity" |

### Hook 2: Error Reporting Check (PostToolUse on Edit/Write)

Runs `scripts/check-error-reporting.js` on any API route file edit. Advisory — warns if `withErrorReporting` / `reportError` / `validateCronSecret` is missing.

### Hook 3: Secret Leak Prevention (PostToolUse on Bash `git commit`)

Runs `scripts/check-no-secrets.sh` before every commit. **Blocking** — exit code 1 stops the commit if secrets are detected.

### Hook 4: Pre-Push Reminder (PostToolUse on Bash `git push`)

Advisory reminder to run `npm run test:pre-push` (TypeScript + alerts + pure function tests).

### Hook 5: Critical Utility Change (PostToolUse on Edit/Write)

When `objective-utils.ts`, `date-utils.ts`, or `cron-auth.ts` is changed, reminds to run `npm run test:unit`.

### Settings File Structure

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "python -c \"...\"" }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "python -c \"...\"" }
        ]
      }
    ]
  }
}
```

**Design principles:**
- Advisory hooks use `stderr` output (visible to Claude but don't block)
- Blocking hooks use non-zero exit codes
- All hooks are Python one-liners that parse JSON stdin (the tool use event)
- Never use hooks for complex logic — keep them under 5 lines

---

## Subagents

Diagnostic agents that spawn with specialized context. All are **read-only** — they investigate, never modify.

| Agent | Purpose | When to Use |
|---|---|---|
| `channel-sync-debugger` | Data parity between API fetches and Firestore | "Google Ads dashboard shows $500 but snapshot has $470" |
| `alert-engine-tester` | Alert logic tracing | "Why isn't CPA_SPIKE firing for client X?" |
| `meta-creative-debugger` | Creative decision explanation | "Why did ad 123 get killed?" |
| `ecommerce-platform-specialist` | Shopify/TN/WooCommerce issues | "Tiendanube orders aren't syncing" |
| `ai-analyst-prompt-engineer` | System prompt debugging | "The meta_ads analyst is giving generic answers" |
| `firestore-query-builder` | Query design + index planning | "Build me a query for channel_snapshots from last 30 days" |
| `cron-health-doctor` | Cron failure correlation | "Morning briefing has been failing for 3 days" |

**When to create a subagent:**
- The diagnosis requires reading 5+ files and cross-referencing data
- You find yourself repeating the same investigation pattern
- The task is read-only (never create subagents that modify code)

---

## Skills

Skills are larger knowledge bundles that auto-activate based on task context.

| Skill | Purpose |
|---|---|
| `worker-brain-guide` | Overall architecture — auto-activates on codebase questions |
| `worker-firestore` | Doc ID patterns, indexes, batch write limits |
| `worker-cron` | Cron skeleton, auth, idempotency, timeout patterns |
| `worker-slack-formatting` | Digest formatting, threads, anti-noise budget |
| `worker-ast-rules` | Static analysis — ast-grep rules for architectural invariants |

**Skill vs Rule vs Command:**
- **Rule**: an invariant that must always hold (law)
- **Command**: a workflow you invoke explicitly (tool)
- **Skill**: domain knowledge that activates contextually (expertise)

---

## AST Rules

Static analysis via [ast-grep](https://ast-grep.github.io/) that enforces architectural invariants structurally (not textually — it parses the AST).

### Rules Shipped

| Rule | Severity | What It Catches |
|---|---|---|
| `no-firestore-in-evaluate` | error | `db.collection()` inside any `evaluate()` method |
| `cron-requires-auth` | error | Cron route missing `validateCronSecret` reference |
| `cron-must-declare-maxDuration` | warning | Cron route without `export const maxDuration` |
| `no-hardcoded-conversion-metric` | warning | Direct `metrics.purchases` / `metrics.leads` instead of `getPrimaryMetric()` |
| `no-console-error-swallow` | warning | `catch` block with only `console.error` (should use `reportError`) |
| `no-null-as-delete-sentinel` | warning | `.update({ field: null })` should use `FieldValue.delete()` |

### Running

```bash
bash .claude/skills/worker-ast-rules/scan.sh        # Full scan
ast-grep scan --rule rules/no-firestore-in-evaluate.yml  # Single rule
```

### When to Add a Rule

All three must be true:
1. The invariant is already documented in `.claude/rules/*.md`
2. You've seen it violated at least once
3. The violation is structural (code shape), not semantic (logic)

---

## How It All Connects

```
User types: /commit-checkpoint
    │
    ├─ Command reads its .md definition
    ├─ Step 1: git diff --stat (what changed?)
    ├─ Step 2: if alert-engine files → /test-alerts
    ├─ Step 3: /ts-check
    ├─ Step 4: propose commit message
    ├─ Step 5: git commit
    │     │
    │     └─ Hook fires: check-no-secrets.sh (blocking)
    │
    └─ Done. User reviews.

User edits: src/lib/alert-engines/google-alert-engine.ts
    │
    ├─ Hook fires: "Run /test-alerts before committing"
    ├─ Hook fires: check-error-reporting.js (advisory)
    │
    └─ On next commit, /commit-checkpoint will catch regressions

User asks: "Why isn't CPA_SPIKE firing for client X?"
    │
    ├─ Subagent: alert-engine-tester spawns
    ├─ Reads engine code + test fixtures
    ├─ Traces the evaluate() logic
    │
    └─ Reports: threshold is 30% but client's delta is 28%
```

### The Enforcement Pyramid

```
         ┌─────────┐
         │  Hooks   │  ← Automatic, every action
         │ (block)  │
         ├──────────┤
         │ AST Rules│  ← On-demand or CI, structural
         │ (scan)   │
         ├──────────┤
         │ Commands │  ← User-invoked workflows
         │ (/slash) │
         ├──────────┤
         │  Rules   │  ← Always-loaded context
         │ (.md)    │
         ├──────────┤
         │ CLAUDE.md│  ← Architecture + reference
         └──────────┘
```

Each layer reinforces the ones below it:
- **CLAUDE.md** teaches Claude the patterns
- **Rules** encode the invariants
- **Commands** execute the verification workflows
- **AST rules** catch structural violations
- **Hooks** make enforcement automatic

---

## Plugins & Development Workflow Skills

Beyond the project-specific setup, we use several **Claude Code plugins** that add development workflow discipline. These are installable plugins — they work across any project.

### Superpowers Plugin

The [superpowers](https://github.com/anthropics/claude-code-plugins) plugin adds 14 skills that enforce disciplined software development. They auto-activate based on context — you don't invoke them manually.

#### The Development Lifecycle

```
  Idea → Brainstorming → Writing Plans → Executing Plans → Verification → Finishing Branch
           ↓                                    ↓
     systematic-debugging              requesting-code-review
     (if bugs found)                   receiving-code-review
```

#### Core Skills

| Skill | When It Activates | What It Enforces |
|-------|------------------|-----------------|
| **brainstorming** | Before any creative work — features, components, modifications | Explores intent, proposes 2-3 approaches with trade-offs, gets design approval BEFORE any code is written. Hard gate: no implementation until design is approved. |
| **writing-plans** | After brainstorming produces a spec | Creates bite-sized implementation plans (2-5 min per step). Each step is one action: write test → verify it fails → implement → verify it passes → commit. Plans are saved to `docs/superpowers/plans/`. |
| **executing-plans** | When a written plan exists | Loads plan, executes task-by-task with checkpoints. Stops on any blocker instead of guessing. Marks progress via TodoWrite. |
| **test-driven-development** | Before writing any implementation code | Red-Green-Refactor cycle. Iron law: no production code without a failing test first. If you wrote code before the test? Delete it. Start over. |
| **systematic-debugging** | On any bug, test failure, or unexpected behavior | Four phases: (1) Root cause investigation, (2) Hypothesis formation, (3) Targeted fix, (4) Verification. Iron law: no fixes without root cause investigation first. |
| **verification-before-completion** | Before claiming work is done | Iron law: no completion claims without fresh verification evidence. "Should pass" is not evidence — run the command and show the output. |
| **dispatching-parallel-agents** | When facing 2+ independent tasks | One agent per independent problem domain. Prevents sequential investigation of unrelated failures. |
| **requesting-code-review** | After completing a feature | Triggers a code review subagent to validate work meets requirements. |
| **receiving-code-review** | When getting review feedback | Requires technical verification of suggestions before implementing — no blind agreement. |
| **finishing-a-development-branch** | When implementation is complete | Guides merge/PR/cleanup decision with structured options. |
| **using-git-worktrees** | Before feature work needing isolation | Creates isolated git worktrees for parallel development. |
| **subagent-driven-development** | For plans with independent tasks | Dispatches parallel agents for non-blocking tasks in the plan. |
| **writing-skills** | When creating new skills | Meta-skill for authoring well-structured skills. |

#### Key Design Principles

1. **Hard gates over soft suggestions.** "No code before design approval" is enforced, not suggested.
2. **Iron laws are non-negotiable.** Each skill has one — the thing that, if violated, invalidates the entire workflow.
3. **Auto-activation over manual invocation.** Skills fire based on context, not user memory.
4. **Chained skills.** Brainstorming → writing-plans → executing-plans → finishing-branch is a pipeline where each step invokes the next.

### Hookify Plugin

[Hookify](https://github.com/anthropics/claude-code-plugins) creates **behavioral rules** that trigger on specific events. Unlike settings.json hooks (which run shell commands), hookify rules are markdown files that inject context or warnings into the conversation.

#### Rule Format

```markdown
---
name: warn-dangerous-rm
enabled: true
event: bash
pattern: rm\s+-rf
---

STOP. You are about to run a recursive force-delete.
Verify the path is correct and not a parent directory.
```

#### Event Types

| Event | Triggers On |
|-------|------------|
| `bash` | Bash tool commands |
| `file` | Edit, Write, MultiEdit tools |
| `stop` | When agent wants to stop working |
| `prompt` | When user submits a prompt |
| `all` | All events |

#### Actions

- `warn` (default) — Shows the message but allows the operation
- `block` — Prevents the operation entirely

Rules are stored as `.claude/hookify.{rule-name}.local.md` files (gitignored by default — personal preferences).

### Learning & Explanatory Mode

We run Claude Code in **learning mode** — a combination of interactive learning with educational explanations. This is configured via session settings (not a plugin).

#### What It Does

Before and after writing code, Claude provides educational insights:

```
★ Insight ─────────────────────────────────────
The functional core / imperative shell pattern keeps all side effects
at the boundary. evaluate() is pure computation — run() is the shell
that fetches data and injects dependencies like referenceDate.
─────────────────────────────────────────────────
```

#### When It Requests User Code Contributions

Instead of implementing everything, Claude identifies spots where the user's input matters:

- Business logic with multiple valid approaches
- Error handling strategies
- Algorithm choices
- UX decisions

It creates the file with context, adds function signatures, and asks the user to write 5-10 lines of meaningful code. Not busy work — decisions that shape the feature.

### Other Useful Plugins

| Plugin | Purpose |
|--------|---------|
| **frontend-design** | Production-grade UI with high design quality, avoids generic AI aesthetics |
| **claude-code-setup** | Analyzes codebase and recommends automations (hooks, skills, subagents) |
| **claude-md-management** | Audits and improves CLAUDE.md files |
| **plugin-dev** | Tools for creating your own plugins (agents, commands, skills, hooks) |
| **skill-creator** | Meta-skill for creating and testing new skills |
| **playground** | Creates interactive HTML playgrounds for visual configuration |

### GSD (Get Shit Done) — Project-Scale Orchestration

[GSD](https://github.com/coleam00/gsd) is a full project management framework for Claude Code. While superpowers handles individual feature development (brainstorm → plan → execute), GSD handles **multi-phase project delivery** with roadmaps, milestones, and parallel agent execution.

#### When to Use GSD vs Superpowers

| Scenario | Use |
|----------|-----|
| Single feature or bug fix | Superpowers (brainstorm → plan → execute) |
| Multi-phase project (5+ phases, dependencies) | GSD (roadmap → phases → wave execution) |
| Greenfield project setup | GSD `/gsd:new-project` |
| Quick task, no planning needed | GSD `/gsd:fast` or just do it |

#### The GSD Lifecycle

```
/gsd:new-project → /gsd:discuss-phase → /gsd:plan-phase → /gsd:execute-phase → /gsd:verify-work
      │                    │                    │                    │
      ▼                    ▼                    ▼                    ▼
  PROJECT.md          Discussion           Research             Wave-based
  ROADMAP.md          + assumptions         → Plan              parallel
  STATE.md            gathering             → Verify            execution
```

#### Research-First Planning (`/gsd:plan-phase`)

GSD doesn't jump to planning — it researches first:

1. **Research phase** — A `gsd-phase-researcher` agent investigates the technical approach, reads docs, checks APIs, and writes `RESEARCH.md`
2. **Planning phase** — A `gsd-planner` agent reads the research and creates detailed `PLAN.md` files with task breakdown
3. **Plan verification** — A `gsd-plan-checker` agent reviews the plan against the phase goal (goal-backward analysis)
4. **Revision loop** — If the checker finds issues, the planner revises (max 3 iterations)

Each step is a **separate subagent** with fresh context — the orchestrator stays lean and coordinates.

#### Wave-Based Parallel Execution (`/gsd:execute-phase`)

This is where GSD shines. Instead of executing tasks sequentially, it groups plans into **waves** based on dependencies:

```
Phase 5: Authentication System
├── Wave 1 (parallel — no dependencies)
│   ├── Plan 01: Database schema + migrations      → Agent A (worktree)
│   └── Plan 02: Auth provider integration          → Agent B (worktree)
├── Wave 2 (parallel — depends on Wave 1)
│   ├── Plan 03: API middleware                     → Agent C (worktree)
│   └── Plan 04: Session management                 → Agent D (worktree)
└── Wave 3 (sequential — depends on Wave 2)
    └── Plan 05: E2E auth flow tests                → Agent E (worktree)
```

**How it works:**

1. **Discover plans** — Reads all `PLAN-*.md` files in the phase directory
2. **Analyze dependencies** — Groups plans into waves by dependency order
3. **Spawn parallel agents** — Each plan gets a `gsd-executor` subagent in an **isolated git worktree** (no merge conflicts)
4. **Wait for wave completion** — Spot-check via SUMMARY.md + git log (handles signal failures)
5. **Post-wave hooks** — Run pre-commit hooks once after all agents finish (they commit with `--no-verify` to avoid contention)
6. **Next wave** — Only starts after all plans in the current wave complete

**Key design decisions:**

- **Worktree isolation** — Each agent gets its own copy of the repo. No merge conflicts between parallel agents.
- **Orchestrator stays lean** — Passes file paths, not content. Agents read files with their fresh context window.
- **Spot-check fallback** — If an agent's completion signal is lost, the orchestrator checks for SUMMARY.md and recent commits to verify success.
- **Interactive mode** — `--interactive` flag runs plans sequentially inline (no subagents) with user checkpoints between tasks. Lower token usage, good for small phases.

#### Other GSD Commands Worth Knowing

| Command | Purpose |
|---------|---------|
| `/gsd:fast` | Inline execution for trivial tasks — no subagents, no planning overhead |
| `/gsd:autonomous` | Run all remaining phases automatically (discuss → plan → execute per phase) |
| `/gsd:debug` | Systematic debugging with persistent state across context resets |
| `/gsd:map-codebase` | Parallel codebase analysis — spawns mapper agents by focus area |
| `/gsd:verify-work` | Conversational UAT — validates features through goal-backward analysis |
| `/gsd:resume-work` | Restores context from previous session via STATE.md |
| `/gsd:manager` | Interactive command center for managing multiple phases |

#### What GSD Teaches About Scaling Claude Code

Even if you don't use GSD directly, its patterns are worth adopting:

1. **State files beat conversation memory.** `STATE.md` persists across sessions. Claude can resume from where it left off without re-reading the entire conversation.
2. **Orchestrator ≠ executor.** The agent that coordinates should NOT be the one writing code. Keep orchestration lean (file paths, not content).
3. **Worktrees solve parallel conflicts.** `isolation: "worktree"` gives each agent its own branch and working directory — zero merge conflicts.
4. **Goal-backward verification.** Don't check "did the tasks complete?" — check "does the codebase achieve the phase goal?" These are different questions.
5. **Research before planning, planning before execution.** Three separate agents, three separate context windows. Each one is focused.

### Installing Plugins

```bash
# Install from the official registry
claude plugins install superpowers
claude plugins install hookify
claude plugins install frontend-design

# GSD uses a different install method
# See: https://github.com/coleam00/gsd
```

Plugins are global (not per-project). Their skills auto-activate across all your projects based on task context.

---

## Adapting This for Your Project

1. **Install superpowers first.** `claude plugins install superpowers` — gives you brainstorming, TDD, verification, and debugging discipline for free across all projects.
2. **Start with CLAUDE.md.** Document your stack, patterns, and the 3-5 rules that matter most.
3. **Extract rules.** When you correct Claude twice for the same thing, create a `.claude/rules/` file.
4. **Add commands.** When you run the same 3 commands in sequence repeatedly, make a slash command.
5. **Wire hooks.** When a rule gets violated despite documentation, add a hook that reminds or blocks.
6. **AST rules last.** Only when you have documented rules that keep getting violated structurally.
7. **Build skills for your domain.** When Claude needs specialized knowledge (your API, your database patterns, your team's conventions), create a skill.

The goal is not maximum configuration — it's zero repeated corrections.
