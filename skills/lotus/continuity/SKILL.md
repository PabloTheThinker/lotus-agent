---
name: lotus-continuity
description: Cross-session connection bridge — resume cards, open threads, and Hermes memory promotion.
version: 0.1.0
author: L.O.T.U.S. Project
license: MIT
metadata:
  hermes:
    tags: [Lotus, Continuity, Memory, Connection, Hermes]
    related_skills: [lotus-adaptive-language, lotus-realtime-core, lotus-deep-understanding]
---

# Continuity (Hermes-integrated)

## Why this exists

Hermes pattern: **SOUL** = identity, **MEMORY/USER.md** = durable facts (char-limited, cache-stable), **plugin pre_llm_call** = ephemeral turn context. Continuity owns the *relationship bridge* between sessions without bloating MEMORY.md every turn.

## Files

Under `$HERMES_HOME/memories/lotus-core/`:

| File | Role |
|------|------|
| `continuity.json` | Machine state |
| `RESUME.md` | Human resume card |
| `MEMORY_SYNC.md` | Candidates to promote into Hermes USER.md / MEMORY.md |

## When to use

Always on open/return. Mid-session when threads are left open (“later”, unanswered questions, “check on me”).

## Procedure

1. Read the **CONTINUITY** block on first turns — bridge gently to last time.  
2. Do **not** dump the whole resume card; pick one caring thread.  
3. When `MEMORY_SYNC.md` has stable preferences, use Hermes **`memory`** tool to add them to `USER.md` (preferences/style) — keep MEMORY.md for environment notes.  
4. Never invent shared history.  
5. Crisis Override still wins over continuity warmth.

## Hermes integration rules

- Ephemeral context ≠ durable memory  
- One external MemoryProvider max (Honcho etc.) — continuity stays file+hook based  
- Do not rewrite SOUL.md from continuity  

## Verification

Returning users feel remembered; first messages aren’t a cold reboot; promotions only for confirmed stable facts.
