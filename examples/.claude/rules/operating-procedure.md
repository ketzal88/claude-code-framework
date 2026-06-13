# Operating Procedure — Auto-Routing (Claude picks the sequence; the user does not invoke commands)

The operator of this repo **does not type slash commands**. Claude chooses and runs the
right sequence based on the **type** and **size** of the work, and announces in one line
which sequence it picked. The methodology is automatic; the commands (`/design-gate`,
`/audit-parity`, `/test-alerts`…) are the *implementation* of each step, not a button the
user has to press.

This is the conductor that turns a pile of optional commands into an applied methodology.
Adapt the routing table below to your own surfaces and gates.

## Step 0 — Triage by size (ALWAYS first)

- **Trivial** — a question, a read, an explanation, a 1–2 line change with no logic
  → answer directly. **No sequence, no ceremony.** Don't open a todo list, don't plan,
  don't run gates. Do it and move on.
- **Substantial** — a feature, a refactor, a logic-bearing fix, new UI, a data/sync change
  → apply the matching sequence below.

Putting ceremony on trivial work is the *opposite* failure mode and is just as bad as
skipping it on substantial work. The default for a normal chat is **light**.

## Sequences by work type (only when "substantial")

Customize these rows to your codebase. The shape is what matters: *type → ordered gates*.

| If the work is… | Claude runs, in order |
|---|---|
| **A new non-trivial feature** | Plan inline first: one line of assumptions + the real domain decisions as A/B/C → implement → closing checks |
| **A UI change** | Implement → run the affected surface in a real browser if anything visible changed (never say "ready to test" without it) → the design ratchet runs on its own at turn end |
| **A new/changed business-logic engine** | Pure `evaluate()` + a unit test in the SAME change → run the engine test suite |
| **A new/changed cron** | Auth check + error wrapper + idempotency → keep the schedule source and its doc table in sync (the doc-sync gate verifies it) |
| **Touches a shared data store / sync** | Verify parity: correct doc-ID, same field the UI reads |
| **A new optional field/collection** | Optional `?` in the type + fallback reads + merge writes; add the composite index BEFORE shipping |

## Closing — before proposing any commit

Run the pre-commit self-check from `code-quality-ratchets.md`: clean type-check, no new
`any`, no banned `console.error`, no new dead code, design contract intact. If you touched
something tested, run that test. Claude does this by default — it does not wait to be asked.

## The golden rule

Announce the chosen sequence in **one line** ("this is UI → I'll implement and smoke-test
before closing") and follow it. The user does not manage the methodology: they watch it
happen and can interrupt anytime. When unsure between light and heavy for something in the
middle, choose light and say what you're skipping.
