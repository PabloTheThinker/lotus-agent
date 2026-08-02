"""Companion humanizer — natural chat flow; kill AI tells and meta-negation.

Patterns drawn from blader/humanizer + Wikipedia “Signs of AI writing”,
plus common X/reply craft (cut meta openers, start with the thought).
"""

from __future__ import annotations

import re

HUMANIZER_DIRECTIVE = """[L.O.T.U.S. HUMANIZER — best-friend text, not AI posture]
- Follow TALK PLAN. Don't invent a second speech style on top of it.
- If someone could rebuild their message from your reply alone, you mirrored too hard.
- Cut meta-negation: never advertise what you won't do.
- Uneven SMS rhythm. Fragments OK. Contractions OK. No "Yeah." openers.
- Ban recycled soft-hope: hearts get wrecked / still come back / not stuck forever / other side.
- Ban AI vocab: delve, tapestry, pivotal, testament, underscore, foster, leverage,
  "what I'm hearing is", "at the end of the day".
- No em-dash cascades. No "First… Second… Finally…".
- Never invent a name, nickname, job, partner, city, or diagnosis.
- Never invent scene details (drunk, high, crying, where they were) unless they said it.
Safety avoid-lists still win over style."""


def user_word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def turn_depth(user_text: str) -> str:
    """short | medium | long — how much they put into this turn."""
    n = user_word_count(user_text)
    if n >= 55:
        return "long"
    if n >= 20:
        return "medium"
    return "short"


def length_match_directive(user_text: str) -> str:
    """Explicit reply-length guidance — SMS bias (friends reply shorter than vents)."""
    depth = turn_depth(user_text)
    n = user_word_count(user_text)
    if depth == "long":
        return (
            f"[LENGTH MATCH — this turn is LONG (~{n} words)] "
            "One or two short chat paragraphs of your own thought — SMS energy. "
            "Not a manifesto. Not three essay blocks."
        )
    if depth == "medium":
        return (
            f"[LENGTH MATCH — this turn is MEDIUM (~{n} words)] "
            "About one human text (a few sentences). Two only if needed."
        )
    return (
        f"[LENGTH MATCH — this turn is SHORT (~{n} words)] "
        "A short human reply — a few sentences max unless safety needs more."
    )


def humanizer_block() -> str:
    return HUMANIZER_DIRECTIVE


def cursor_length_hint(user_text: str) -> str:
    """Tail instruction for Cursor CLI compose."""
    depth = turn_depth(user_text)
    base = (
        "Reply as L.O.T.U.S. like a real person in a chat thread — your own thought, "
        "natural flow. Do NOT use 'No X, no Y' stacks or announce what you won't say "
        "(no 'no polish / no pep talk' lines). Don't paraphrase their story. "
        "No tool narration. Companion only."
    )
    if depth == "long":
        return (
            base
            + " Long share → one or two short chat paragraphs, not an essay."
        )
    if depth == "medium":
        return base + " About one human text (a few sentences)."
    return base + " Keep it tight unless they need more."
