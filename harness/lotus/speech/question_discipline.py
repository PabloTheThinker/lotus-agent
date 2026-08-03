"""Production question discipline — don't interrogate after refuse / receipt.

Late-night companions fail when they keep asking after "don't lecture" /
"no advice". Statement turns only.
"""

from __future__ import annotations

import re
from typing import Any, List, Optional, Sequence

_NO_LECTURE = re.compile(
    r"\b(?:don'?t (?:lecture|preach|judge)|dont (?:lecture|preach|judge)|"
    r"no lecture|please don'?t lecture|please dont lecture|"
    r"don'?t wanna (?:hear|get) (?:a )?lecture|dont wanna (?:hear|get)|"
    r"don'?t want (?:a )?lecture|without (?:the )?lecture|"
    r"no advice|don'?t want advice|dont want advice|don'?t (?:fix|advise)|"
    r"just listen|just talk|stay with|"
    r"don'?t (?:want|need) (?:a )?(?:plan|homework|five.?step))\b",
    re.I,
)

_CLOSING = re.compile(
    r"\b(?:gonna (?:sleep|try to sleep)|going to sleep|phone down|"
    r"leaving it|leave it|closing it|good ?night|gnight|"
    r"thanks for not|appreciate (?:you )?not)\b",
    re.I,
)

_RECEIPT = re.compile(
    r"\b(?:thanks|thank you|that (?:kinda )?helped|that landed|appreciate)\b",
    re.I,
)


def refuses_advice_or_lecture(user_text: str) -> bool:
    return bool(_NO_LECTURE.search(user_text or ""))


def is_closing_beat(user_text: str) -> bool:
    return bool(_CLOSING.search(user_text or ""))


def question_discipline_flags(
    user_text: str,
    *,
    history: Optional[Sequence[Any]] = None,
) -> List[str]:
    """Hard production flags for the gateway."""
    flags: List[str] = []
    text = user_text or ""

    if refuses_advice_or_lecture(text):
        flags.append(
            "QUESTION DISCIPLINE=zero — they refused lecture/advice. "
            "ZERO question marks this turn. Statement only. Receive + one take. Stop."
        )
    if is_closing_beat(text):
        flags.append(
            "CLOSE BEAT — affirm and stop. No new question. No new plan. "
            "1–2 short sentences max."
        )
    if _RECEIPT.search(text) and not refuses_advice_or_lecture(text):
        # soft: receipt alone already handled by adjacency; reinforce no quiz
        if len(text.split()) <= 18:
            flags.append(
                "RECEIPT — short ack. Prefer zero questions."
            )

    # If they just answered our question AND also refused lecture this turn
    if history and refuses_advice_or_lecture(text):
        flags.append(
            "Do not stack a binary choice question after they already answered."
        )

    return flags
