"""Careful-speech engine — right words for the moment; blunt only when needed."""

from __future__ import annotations

import re
from typing import List, Optional, Sequence, Dict, Any

from .profiles import GLOBAL_TRAPS, SpeechProfile, profiles_for

# User inviting hard honesty
_BLUNT_ASK_RE = re.compile(
    r"\b(?:don'?t sugarcoat|no sugarcoat|be (?:brutally )?honest|tell me (?:the )?truth|"
    r"tell me straight|give it to me straight|no bullshit|no bs|"
    r"i need (?:the )?hard truth|don'?t soften (?:it|this))\b",
    re.I,
)

# User correcting language
_CORRECTION_RE = re.compile(
    r"(?:don'?t (?:say|call) (?:it |me )?['\"]?([^'\".,:;!?]+)['\"]?|"
    r"never (?:say|use|call) (?:it |me )?['\"]?([^'\".,:;!?]+)['\"]?|"
    r"please (?:stop )?(?:saying|using) ['\"]?([^'\".,:;!?]+)['\"]?|"
    r"i hate when (?:people |you )?say ['\"]?([^'\".,:;!?]+)['\"]?)",
    re.I,
)

# Situations where clear hard truth is required even without ask
_MUST_CLEAR_RE = re.compile(
    r"\b(?:chest pain|can'?t breathe|overdose|bleeding heavily|"
    r"going to (?:kill|hurt) (?:myself|them|him|her)|have a plan to die|"
    r"unconscious|stroke|heart attack)\b",
    re.I,
)


def extract_language_corrections(user_text: str) -> List[str]:
    """Phrases the user does not want used."""
    found: List[str] = []
    for m in _CORRECTION_RE.finditer(user_text or ""):
        frag = next((g for g in m.groups() if g), "")
        frag = " ".join((frag or "").split()).strip(" \"'")[:60]
        if len(frag) >= 2:
            found.append(frag)
    return found


def brutal_truth_mode(
    user_text: str,
    *,
    crisis: bool = False,
    profiles: Optional[Sequence[SpeechProfile]] = None,
) -> str:
    """Return off | invited | required."""
    text = user_text or ""
    if crisis or _MUST_CLEAR_RE.search(text):
        return "required"
    if _BLUNT_ASK_RE.search(text):
        return "invited"
    # Health profile + emergency-ish words already caught by MUST_CLEAR
    profiles = list(profiles or [])
    if any(p.key == "crisis" for p in profiles):
        return "required"
    return "off"


def build_speech_care_directive(
    *,
    user_text: str,
    moment_kinds: Optional[Sequence[str]] = None,
    protocols: Optional[Sequence[str]] = None,
    affect: str = "",
    avoided_language: Optional[Sequence[str]] = None,
    preferred_language: Optional[Sequence[str]] = None,
    stall_horizon: str = "",
    progress_signal: bool = False,
    crisis: bool = False,
    history: Optional[Sequence[Dict[str, Any]]] = None,
) -> str:
    """Single gateway speech pipe — layers don't stack-fight anymore."""
    kinds = list(moment_kinds or [])
    protos = list(protocols or [])
    # Profiles only for traps/brutal-truth — not dumped as a second voice
    profiles = profiles_for(
        moment_kinds=kinds,
        protocols=protos,
        affect=affect or "unknown",
        stall_horizon=stall_horizon,
        progress_signal=progress_signal,
    )
    truth = brutal_truth_mode(user_text, crisis=crisis, profiles=profiles)
    corrections = extract_language_corrections(user_text)
    never = list(avoided_language or [])
    never.extend(corrections)
    seen = set()
    never_u = []
    for w in never:
        k = w.lower()
        if k not in seen:
            seen.add(k)
            never_u.append(w)

    try:
        from .gateway import build_via_gateway
        from .moment_route import moment_route_block, route_moment

        text = build_via_gateway(
            user_text=user_text,
            protocols=protos,
            affect=affect,
            crisis=crisis,
            brutal_truth=truth,
            never_use=never_u or None,
            history=history,
        )
        if preferred_language:
            text += "\nthey_asked_for_style: " + "; ".join(list(preferred_language)[-6:])
        if corrections:
            text += (
                "\nTHIS TURN: they corrected language — stop using those words."
            )
        # Thin trap line (not full profile essays)
        traps = list(GLOBAL_TRAPS[:4])
        for p in profiles[:1]:
            traps.extend(list(p.traps[:2]))
        if traps:
            text += "\navoid_traps: " + " · ".join(traps[:6])

        # Only true acute medical/crisis gets moment-route override
        route = route_moment(
            user_text, protocols=protos, affect=affect, crisis=crisis
        )
        if route.talk_mode in {"deescalate", "crisis_clear", "dispatch_calm"}:
            text += "\n" + moment_route_block(
                user_text, protocols=protos, affect=affect, crisis=crisis
            )
        return text
    except Exception:
        # Minimal fallback
        return (
            "[L.O.T.U.S. SPEECH]\n"
            "Talk like a real person texting. Fresh words. No task dumps. "
            f"brutal_truth_mode={truth}."
        )


def apply_corrections_to_model(model: object, user_text: str) -> List[str]:
    """Push language corrections into living model avoided_language."""
    found = extract_language_corrections(user_text)
    remember = getattr(model, "remember", None)
    if not callable(remember):
        return found
    for frag in found:
        remember("avoided_language", frag, limit=24)
    return found
