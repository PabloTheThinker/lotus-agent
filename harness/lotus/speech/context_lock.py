"""Shared context-lock rules — Hermes + Cursor backends get the same hard rules.

Lock = no inventing. Stated facts are allowed and should be used.
"""

from __future__ import annotations

CONTEXT_LOCK = """[CONTEXT LOCK — non-negotiable]
- USE facts the user actually said in this thread (and prior turns). Stay in that moment.
- NEVER invent scene details they did not say: drunk, high, crying, motives, places,
  what was in a text, names, jobs, diagnoses — unless THEY said it.
- If they said they're drunk / high / crying / in the ER → name it and help inside
  THAT moment. Do not pretend those words are banned.
- If you don't know → ASK. Don't fill gaps with a story that "sounds right."
- Build the next reply on their words — not a guess, and not a digression.
"""


def context_lock_block() -> str:
    return CONTEXT_LOCK.strip()
