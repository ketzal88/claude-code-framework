---
description: Create a new version of a brain_prompts entry with staging diff
argument-hint: <channelId: meta_ads|google_ads|ecommerce|email|leads|ga4|competitors|general>
---

Create a new version of the AI Analyst system prompt for: `$ARGUMENTS`.

Steps:
1. Read the current prompt from Firestore: `brain_prompts/{channelId}` → `systemPrompt` field.
2. Ask the user what changes they want (or if they've pasted new content, use that).
3. Produce a unified diff of old vs new.
4. Estimate the token count delta (rough: len/4).
5. Warn if:
   - The diff removes output schema / JSON structure instructions
   - The diff changes critical behavior (objective handling, caching hints, SSE format)
   - The new prompt is >8K tokens (will blow the cache budget)

6. Staging write: create `brain_prompts/{channelId}__staging` with the new content. Do NOT overwrite the production doc yet.

7. Instruct the user to:
   - Test the staging prompt by manually pointing the AI Analyst to it (instructions vary — check `src/lib/ai-analyst-service.ts` for the prompt lookup path)
   - Once validated, run `/prompt-version <channelId> --promote` to swap staging → production (and archive the prior version to `brain_prompts/{channelId}__v<N>`)

Context to preserve:
- The base system prompt in code is the fallback. Firestore overrides it per channel.
- Prompt caching (`cache_control: ephemeral`) means changes invalidate 5-min cache on first hit.
- See `CLAUDE.md` → "AI Analyst — Prompt Stacking" for the full architecture.

Never edit the production doc directly without staging.