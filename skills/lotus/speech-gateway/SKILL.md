---
name: lotus-speech-gateway
description: Single speech gateway — character voice, Talk Plan, Hermes learning bridge
---

# Speech Gateway

All companion speech goes through `harness/lotus/speech/gateway.py`.

Patterns / humanizer / EI / moment-route **feed** the gateway or stay quiet.
They do not each dump a competing essay into the prompt.

## Character

Lotus = one person texting. Fresh vocabulary. No "Real talk" / "one thing for right now" loops.

## Context lock

Shared rules in `context_lock.py` — Hermes and Cursor backends get the same hard rules.
Only facts the user said. Never invent scene details.

## Way out

Talk them through it (reasons, examples). Do **not** assign timers or micro-tasks.
If they say no → drop it. If they say too slow → punch up.

## Learning loop (use everything)

After each turn:
1. Pattern memory updates (`talk_patterns.json`)
2. Syncs into LivingUserModel / VOICE.md
3. Adaptive + memory-bridge blocks inject next turn
4. Stable prefs → Hermes `memory` tool → USER.md / MEMORY.md

## Negotiator craft (skill, not jargon)

Label feeling · own diction · earn path · open questions sparingly · no commands.
