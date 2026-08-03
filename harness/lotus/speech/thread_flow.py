"""Conversation thread flow — reply to what was just said (adjacency).

Scripted transcripts ignored Lotus's questions. Real chat needs:
- if Lotus asked something and the user answers → receive that answer
- don't re-ask the same question; advance the thread
"""

from __future__ import annotations

import re
from typing import Any, Optional, Sequence

_QUESTION_SPLIT = re.compile(r"(?<=[?])\s+")


def last_assistant_question(history: Optional[Sequence[Any]]) -> str:
    """Return the last question Lotus asked (last sentence with '?'), if any."""
    if not history:
        return ""
    for turn in reversed(list(history)):
        if not isinstance(turn, dict):
            continue
        if str(turn.get("role") or "") != "assistant":
            continue
        text = str(turn.get("content") or "").strip()
        if not text or "?" not in text:
            continue
        # Prefer the last interrogative sentence
        parts = re.split(r"(?<=[.!?])\s+", text)
        qs = [p.strip() for p in parts if "?" in p]
        if qs:
            return qs[-1][:220]
        return text[:220]
    return ""


def _looks_like_answer(user_text: str, question: str) -> bool:
    """Heuristic: user is continuing / answering, not a brand-new unrelated dump."""
    u = (user_text or "").strip().lower()
    if not u or not question:
        return False
    # Explicit answer cues
    if u.startswith(
        (
            "because",
            "cause",
            "i guess",
            "idk",
            "i don't know",
            "loneliness",
            "lonely",
            "anger",
            "angry",
            "both",
            "the words",
            "them not",
            "yeah",
            "nah",
            "maybe",
            "mostly",
            "honestly",
        )
    ):
        return True
    # Short reply after a question often is the answer
    if len(u.split()) <= 28 and "?" not in u:
        return True
    # Shared content words with the question
    q_words = {w for w in re.findall(r"[a-z']{4,}", question.lower()) if w not in {
        "what", "were", "you", "your", "that", "this", "with", "when", "harder",
        "actually", "reaching", "hitting", "about", "they", "them",
    }}
    u_words = set(re.findall(r"[a-z']{4,}", u))
    if q_words and len(q_words & u_words) >= 1:
        return True
    return False


def thread_flow_directive(
    user_text: str,
    *,
    history: Optional[Sequence[Any]] = None,
) -> str:
    """Inject adjacency: answer their answer; don't restart the scene."""
    q = last_assistant_question(history)
    if not q:
        return (
            "[THREAD] No open question from you last turn. "
            "Respond to what they just said — one beat forward."
        )

    lines = [
        "[THREAD — real conversation]",
        f"You asked last: {q}",
    ]
    try:
        from .question_discipline import is_closing_beat, refuses_advice_or_lecture

        no_q = refuses_advice_or_lecture(user_text) or is_closing_beat(user_text)
    except Exception:
        no_q = False

    if _looks_like_answer(user_text, q):
        lines.extend(
            [
                "They are answering / continuing that thread.",
                "RECEIVE their answer. Name it briefly. Then one new move "
                "(take, gentle follow, or quiet) — do NOT re-ask the same question.",
                "Stay in this moment. Don't reset the scene or invent a new topic.",
            ]
        )
        if no_q:
            lines.append(
                "HARD: they also refused lecture/advice or are closing — "
                "ZERO '?' this turn. Statement only."
            )
    else:
        lines.extend(
            [
                "They may have moved sideways — still ground lightly on what they said now.",
                "If your old question still matters, fold it in once; don't interrogate.",
            ]
        )
        if no_q:
            lines.append("HARD: ZERO '?' this turn — no interrogation.")
    return "\n".join(lines)
