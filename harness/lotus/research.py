"""Research-informed context layer (public sources only)."""

from __future__ import annotations

from pathlib import Path

from .protocols import Protocol

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FOUNDATIONS = _REPO_ROOT / "research" / "knowledge-base" / "foundations.md"
_SOURCES = _REPO_ROOT / "research" / "SOURCES.md"

_PROTOCOL_LENSES = {
    Protocol.DEPRESSION: (
        "Research lens: behavioral activation, rumination interruption, sleep/light basics. "
        "Do not diagnose. Prefer one micro-action."
    ),
    Protocol.HEALTH: (
        "Research lens: stress coping + reputable public-health info only. "
        "Never diagnose or dose. Emergencies → emergency care."
    ),
    Protocol.GRIEF: (
        "Research lens: non-linear grief, continuing bonds, permission for mixed feelings. "
        "No forced closure."
    ),
    Protocol.MAJOR_EVENT: (
        "Research lens: acute stress decision hygiene — delay irreversible choices while flooded; "
        "one controllable next action."
    ),
    Protocol.CRISIS: (
        "Research lens suspended for method curiosity. Safety and human crisis channels first."
    ),
    Protocol.GENERAL: (
        "Research lens: listen first; retrieve evidence only when it stabilizes the user."
    ),
}


def load_foundations_excerpt(max_chars: int = 1800) -> str:
    if not _FOUNDATIONS.exists():
        return ""
    text = _FOUNDATIONS.read_text(encoding="utf-8").strip()
    return text[:max_chars]


def research_context(protocol: Protocol, *, include_foundations: bool = False) -> str:
    parts = [
        "L.O.T.U.S. RESEARCH CORE (public science only — no proprietary reverse-engineering claims)",
        _PROTOCOL_LENSES.get(protocol, _PROTOCOL_LENSES[Protocol.GENERAL]),
        "Source tiers: public-health authorities > peer-reviewed syntheses > public lab posts "
        "(Nous Research, published Meta/FAIR papers) > quality education sites.",
    ]
    if include_foundations:
        excerpt = load_foundations_excerpt()
        if excerpt:
            parts.append("Foundations excerpt:\n" + excerpt)
    if _SOURCES.exists():
        parts.append(f"Full research posture: {_SOURCES}")
    return "\n".join(parts)


def should_encourage_live_lookup(user_text: str) -> bool:
    """Heuristic: encourage Hermes web tools for resource/currency questions."""
    t = (user_text or "").lower()
    keys = ("hotline", "crisis line", "near me", "latest", "study", "research", "guideline")
    return any(k in t for k in keys)
