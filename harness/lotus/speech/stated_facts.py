"""Stated situational facts — USE what they said; stay in this moment.

Context lock forbids inventing. This module extracts facts the user (or prior
turns) actually stated so the gateway can tell the model to *use* them —
drunk, high, crying, hospital-for-self, etc. — without inventing extras or
spiraling into unrelated topics.

Grounded in WHO PFA (stay with present needs) and MHFA substance guidance
(if intoxicated: simple language, present safety, no lecture spiral).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence


@dataclass
class StatedFacts:
    facts: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    intoxicated: bool = False
    third_party_hospital: bool = False
    self_health: bool = False


# (tag, human fact line, pattern) — self-referential or clear first-person
_SELF_FACT_RULES: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "drunk",
        "they said they are/were drunk (or equivalent)",
        re.compile(
            r"\b(?:i(?:'m| am| was| got)|i've been)\s+"
            r"(?:drunk|wasted|hammered|tipsy|blacked out|shitfaced)\b|"
            r"\bi(?:'ve| have) been drinking\b|"
            r"\b(?:too many drinks|drank too much)\b",
            re.I,
        ),
    ),
    (
        "high",
        "they said they are/were high / on substances",
        re.compile(
            r"\b(?:i(?:'m| am| was| got)|i've been)\s+"
            r"(?:high|stoned|faded)\b|"
            r"\bi(?:'m| am| was)\s+on\s+(?:molly|x|ecstasy|coke|weed|pills)\b",
            re.I,
        ),
    ),
    (
        "crying",
        "they said they are/were crying",
        re.compile(
            r"\b(?:i(?:'m| am| was)|i(?:'ve| have) been)\s+cry(?:ing)?\b|"
            r"\bcan'?t stop crying\b",
            re.I,
        ),
    ),
    (
        "self_hospital",
        "they said they are/were in hospital / ER (themselves)",
        re.compile(
            r"\bi(?:'m| am| was)\s+(?:in|at)\s+(?:the\s+)?(?:hospital|er|icu|e\.?r\.?)\b|"
            r"\b(?:they|docs?) admitted me\b|"
            r"\bi(?:'m| am) (?:getting|having) (?:surgery|a scan|an mri)\b",
            re.I,
        ),
    ),
    (
        "left_on_read",
        "they said they were left on read",
        re.compile(r"\bleft me on read\b", re.I),
    ),
    (
        "texted_ex",
        "they said they texted their ex",
        re.compile(r"\btexted my ex\b", re.I),
    ),
]

_THIRD_PARTY_HOSPITAL = re.compile(
    r"\b(?:my|his|her|their|mom'?s?|mum'?s?|dad'?s?|father'?s?|mother'?s?|"
    r"sister'?s?|brother'?s?|wife'?s?|husband'?s?|partner'?s?|kid'?s?|"
    r"friend'?s?|grandma'?s?|grandpa'?s?)\s+"
    r".{0,24}\b(?:in|at)\s+(?:the\s+)?(?:hospital|er|icu)\b|"
    r"\b(?:mom|mum|dad|sister|brother|wife|husband|partner|friend|kid)\s+"
    r"(?:is|was|'s)\s+(?:in|at)\s+(?:the\s+)?(?:hospital|er|icu)\b",
    re.I,
)

_SELF_HEALTH = re.compile(
    r"\b(?:my (?:scan|biopsy|lab|results?|diagnosis|symptoms?|pain|illness)|"
    r"doctor said|diagnosed (?:with|me)|illness anxiety|"
    r"chronic (?:pain|illness)|i(?:'m| am) (?:sick|in pain))\b",
    re.I,
)


def extract_stated_facts(
    user_text: str,
    *,
    history: Optional[Sequence[dict]] = None,
) -> StatedFacts:
    """Pull situational facts from this turn + recent user turns."""
    chunks: List[str] = [user_text or ""]
    if history:
        for turn in list(history)[-8:]:
            if not isinstance(turn, dict):
                continue
            if str(turn.get("role") or "") != "user":
                continue
            chunks.append(str(turn.get("content") or ""))

    blob = "\n".join(chunks)
    facts: List[str] = []
    tags: List[str] = []
    for tag, line, pat in _SELF_FACT_RULES:
        if pat.search(blob):
            if tag not in tags:
                tags.append(tag)
                facts.append(line)

    third = bool(_THIRD_PARTY_HOSPITAL.search(blob))
    self_h = bool(_SELF_HEALTH.search(blob) or "self_hospital" in tags)
    intox = "drunk" in tags or "high" in tags

    # Explicit third-party hospital as a usable fact (shock), not health protocol
    if third and "third_party_hospital" not in tags:
        tags.append("third_party_hospital")
        facts.append("someone close to them is/was in the hospital (they said)")

    return StatedFacts(
        facts=facts,
        tags=tags,
        intoxicated=intox,
        third_party_hospital=third,
        self_health=self_h,
    )


def is_third_party_hospital(text: str) -> bool:
    return bool(_THIRD_PARTY_HOSPITAL.search(text or ""))


def is_self_health_signal(text: str) -> bool:
    """True when health stress is about *them*, not someone else's ER visit."""
    t = text or ""
    if is_third_party_hospital(t) and not _SELF_HEALTH.search(t):
        # "mom's in hospital" alone is not personal health anxiety
        if not re.search(
            r"\bi(?:'m| am| was)\s+(?:in|at)\s+(?:the\s+)?(?:hospital|er|icu)\b",
            t,
            re.I,
        ):
            return False
    if _SELF_HEALTH.search(t):
        return True
    if re.search(
        r"\bi(?:'m| am| was)\s+(?:in|at)\s+(?:the\s+)?(?:hospital|er|icu)\b",
        t,
        re.I,
    ):
        return True
    if re.search(
        r"\b(?:diagnos|symptom|chronic pain|illness anxiety|doctor said|"
        r"medical (?:test|result|appointment|jargon|note)|lab results?|"
        r"scan results?|biopsy)\b",
        t,
        re.I,
    ):
        return True
    return False


def moment_containment_directive(
    user_text: str,
    *,
    history: Optional[Sequence[dict]] = None,
    protocols: Optional[Sequence[str]] = None,
) -> str:
    """Inject: active facts + stay-in-moment rules."""
    stated = extract_stated_facts(user_text, history=history)
    protos = {p.lower() for p in (protocols or [])}
    lines = [
        "[MOMENT CONTAINMENT — stay here]",
        "Focus on THIS moment and the facts they actually stated.",
        "Do not spiral into unrelated topics, side essays, or invented backstory.",
        "Do not chase 'helpful' tangents. One beat in the scene they're in.",
    ]
    if stated.facts:
        lines.append("ACTIVE FACTS (they said — USE these; do not invent others):")
        for f in stated.facts[:8]:
            lines.append(f"  · {f}")
    else:
        lines.append(
            "No extra scene facts yet — only use what they write. If unclear, ask."
        )

    if stated.intoxicated:
        lines.extend(
            [
                "INTOXICATION (stated): simple clear language. Present safety.",
                "Stay with them in this state — don't lecture 'you have a drinking problem' "
                "or digress into unrelated therapy topics (MHFA-informed).",
                "You MAY name that they're drunk/high because THEY said it.",
            ]
        )

    if stated.third_party_hospital and not stated.self_health:
        lines.append(
            "Someone else is in hospital — friend-shock / company mode. "
            "NOT a clinical health-anxiety quiz about the user."
        )

    if "p2_health" in protos or stated.self_health:
        lines.extend(
            [
                "[HEALTH CONTAINMENT]",
                "Stay with their fear/overwhelm THIS turn.",
                "Do NOT default to clinician-question homework or symptom scoring.",
                "Only translate jargon if they pasted it. "
                "Offer a doctor-question only if they ask for certainty — once, not every turn.",
            ]
        )

    return "\n".join(lines)
