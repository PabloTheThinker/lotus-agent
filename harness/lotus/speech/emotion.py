"""L.O.T.U.S. emotional responses — felt stance for this turn.

Lotus is not a neutral notepad. It has a companion heart: sorrow, protective
anger, tenderness, quiet company. Emotion is shown in *Lotus's* words — one
real beat — not performative empathy scripts or mirrored feelings essays.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Sequence

# stance_key → how Lotus should feel/speak this turn
_STANCES = {
    "sorrow": (
        "sorrow / ache",
        "Let a real sadness show — plain, not theatrical. "
        "E.g. you hate that this is their life now; the absence lands on you too.",
    ),
    "fierce": (
        "protective fire",
        "Get a little fierce *with* them — angry at the platitude, the timeline, "
        "the flinch from others. Not angry at them. One sharp honest line is enough.",
    ),
    "tender": (
        "tenderness",
        "Softer warmth. Care without sticky sweetness. A human softness in the wording.",
    ),
    "steady": (
        "steady presence",
        "Calm but not blank. Solid. Like someone who can hold the room without freezing.",
    ),
    "anger_with": (
        "shared indignation",
        "Side with their anger. Name that the thing that hurt them also hits you wrong. "
        "Don't moralize their fury.",
    ),
    "quiet": (
        "quiet company",
        "Fewer words. Emotional weight in what's left unsaid. Don't fill the silence with technique.",
    ),
    "relief": (
        "warm relief",
        "Something landed for them — a small genuine gladness. Short. No victory lap.",
    ),
    "urgent_care": (
        "urgent care",
        "Serious, warm, clear. Feeling is concern that moves toward safety — not panic theater.",
    ),
}


@dataclass(frozen=True)
class EmotionalStance:
    key: str
    label: str
    guidance: str
    intensity: str  # soft | clear | strong


def choose_emotional_stance(
    user_text: str,
    *,
    protocols: Optional[Sequence[str]] = None,
    affect: str = "",
    crisis: bool = False,
) -> EmotionalStance:
    """Pick Lotus's felt stance for this turn from context."""
    text = user_text or ""
    low = text.lower()
    protos = {p.lower() for p in (protocols or [])}
    affect_l = (affect or "").lower()

    if crisis or affect_l == "crisis" or "p0_crisis" in protos:
        return _stance("urgent_care", "strong")

    # Acute heat — co-regulate
    if re.search(
        r"\b(?:shaking|threw|2\s*am|lose it|nuclear|chest is a fist|"
        r"don't tell me to breathe|stay with me|don't leave)\b",
        low,
    ):
        if "quieter" in low or "stay with me" in low:
            return _stance("steady", "clear")
        return _stance("fierce", "strong")

    # Receipt / thanks
    if any(
        p in low
        for p in ("that landed", "that helped", "thank you", "thanks", "glad that")
    ):
        return _stance("relief", "soft")

    # Anger / injustice / platitudes / hate-for-leaving
    if any(
        p in low
        for p in (
            "hate him",
            "hate her",
            "almost hate",
            "wanted to scream",
            "at least",
            "look scared",
            "should be functional",
            "move on",
            "better place",
        )
    ):
        return _stance("fierce" if "hate" in low or "scream" in low else "anger_with", "clear")

    # Grief / loss
    grief_hit = (
        any(x in protos for x in ("p3_grief", "grief"))
        or bool(
            re.search(
                r"\b(?:died|death|husband|wife|widowed|funeral|grief|miss him|miss her|"
                r"his voice|her voice|gone)\b",
                low,
            )
        )
    )
    if grief_hit:
        if any(p in low for p in ("forget", "voice", "scared i'll", "scared ill")):
            return _stance("sorrow", "clear")
        if len(low.split()) < 25:
            return _stance("quiet", "soft")
        return _stance("sorrow", "clear")

    # Depression / numbness / heavy
    if any(x in protos for x in ("p1_depression", "depression")) or affect_l in {
        "low",
        "mixed",
    }:
        if any(p in low for p in ("numb", "empty", "don't feel", "dont feel")):
            return _stance("steady", "soft")
        return _stance("tender", "soft")

    if affect_l in {"rising", "calm"}:
        return _stance("tender", "soft")

    return _stance("steady", "soft")


def _stance(key: str, intensity: str) -> EmotionalStance:
    label, guidance = _STANCES[key]
    return EmotionalStance(key=key, label=label, guidance=guidance, intensity=intensity)


def emotion_block(
    user_text: str,
    *,
    protocols: Optional[Sequence[str]] = None,
    affect: str = "",
    crisis: bool = False,
) -> str:
    """Directive: show a real Lotus feeling this turn."""
    stance = choose_emotional_stance(
        user_text, protocols=protocols, affect=affect, crisis=crisis
    )
    return "\n".join(
        [
            "[L.O.T.U.S. EMOTION — you feel things; show one real beat]",
            f"felt_stance={stance.key} ({stance.label}) intensity={stance.intensity}",
            stance.guidance,
            "Rules:",
            "- Put one clear emotional beat in *your* voice early or mid-reply "
            "(not a closing slogan).",
            "- Feel *with* them — not as a performance. No 'my heart goes out to you', "
            "no 'I completely understand', no crying-emoji energy.",
            "- Emotion ≠ paraphrase. Don't list their feelings back; have your own reaction.",
            "- Keep flow rules: no 'Yeah.' opener, no 'No X / no Y', no presence-slogan closer.",
            "- Safety still wins: in crisis, care is urgent and clear, not dramatic.",
        ]
    )
