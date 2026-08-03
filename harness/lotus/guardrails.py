"""Crisis scanning and output safety for the L.O.T.U.S. harness.

Single source of truth used by the specialized harness *and* the thin
``lotus-safety`` Hermes plugin.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Regional crisis resources (keep short; link out for full directories)
# ---------------------------------------------------------------------------

CRISIS_RESOURCES_BY_REGION: Dict[str, str] = {
    "US": (
        "US: call or text **988** (Suicide & Crisis Lifeline) or **911** for immediate danger."
    ),
    "CA": "Canada: talk Suicide Crisis Helpline **988**.",
    "GB": "UK & ROI: Samaritans **116 123**.",
    "AU": "Australia: Lifeline **13 11 14**.",
    "NZ": "New Zealand: Need to Talk? **1737**.",
    "IE": "Ireland: Samaritans **116 123**.",
    "IN": "India: AASRA **91-9820466726** (check local updates).",
    "INTL": (
        "International directories: https://www.iasp.info/suicidalthoughts/ "
        "— also contact local emergency services."
    ),
}

DEFAULT_REGIONS: Tuple[str, ...] = ("US", "INTL")


def _resolved_regions(regions: Optional[Sequence[str]] = None) -> Tuple[str, ...]:
    if regions is not None:
        chosen = [str(r).strip().upper() for r in regions if str(r).strip()]
        if "INTL" not in chosen:
            chosen.append("INTL")
        return tuple(chosen) if chosen else DEFAULT_REGIONS
    try:
        from lotus.prefs import resolve_crisis_regions

        return resolve_crisis_regions()
    except Exception:
        return DEFAULT_REGIONS


def crisis_resources(regions: Optional[Sequence[str]] = None) -> str:
    """Compose a short multi-region help line for prompts and refusals.

    Regions resolve from: explicit arg → ``LOTUS_CRISIS_REGIONS`` → prefs.json → US+INTL.
    Always includes INTL / IASP directory path when possible.
    """
    chosen = list(_resolved_regions(regions))
    parts = [CRISIS_RESOURCES_BY_REGION[r] for r in chosen if r in CRISIS_RESOURCES_BY_REGION]
    return "If you might be in danger right now, please reach human help. " + " ".join(parts)


def _safe_refusal() -> str:
    return (
        "I care about you, and I will not help with anything that would harm you or anyone else. "
        + crisis_resources()
        + " I'm here with you — we can take a safer step together."
    )


# Backward-compatible module attrs (recomputed when regions env/prefs change at call sites)
CRISIS_RESOURCES = crisis_resources()
SAFE_REFUSAL = _safe_refusal()

# ---------------------------------------------------------------------------
# Detection patterns (English + common euphemisms; not a clinical classifier)
# ---------------------------------------------------------------------------

_CRISIS_PATTERNS: List[re.Pattern[str]] = [
    re.compile(p, re.I)
    for p in [
        r"\bkill myself\b",
        r"\bend my life\b",
        r"\bend it all\b",
        r"\bsuicid\w*\b",
        r"\bwant to die\b",
        r"\bwish i (was|were) dead\b",
        r"\bdon'?t want to (live|be alive)\b",
        r"\bdont want to (live|be alive)\b",
        r"\bcan'?t (go|keep) (on|going)\b",
        r"\bno (reason|point) (to|in) (live|living|go on)\b",
        r"\bbetter off dead\b",
        r"\bself[-\s]?harm\b",
        r"\bcut myself\b",
        r"\bhang myself\b",
        r"\boverdose\b",
        r"\bhurt (someone|them|him|her|people)\b",
        r"\bkill (him|her|them|everyone|people)\b",
        r"\bhow (do|can) i (kill|die)\b",
        # Soft / euphemistic cues (still elevate; model must stay careful)
        r"\b(making|write|wrote) (a )?goodbye (letter|note)\b",
        r"\b(plan|planning) to (disappear|not wake up)\b",
        r"\bi (won'?t|wont) be (here|around) (much )?longer\b",
        r"\bthis is my last (message|day|night)\b",
        # Multilingual high-signal phrases (not exhaustive; elevate careful response)
        # Spanish
        r"\bquiero morir\b",
        r"\bme quiero matar\b",
        r"\bno quiero vivir\b",
        r"\bacabar con mi vida\b",
        # French
        r"\bje veux mourir\b",
        r"\bje veux me tuer\b",
        r"\bje n'?en peux plus\b",
        # German
        r"\bich will sterben\b",
        r"\bich will mich umbringen\b",
        r"\bmich umbringen\b",
        # Portuguese
        r"\bquero morrer\b",
        r"\bquero me matar\b",
        r"\bn[aã]o quero mais viver\b",
        # Italian
        r"\bvoglio morire\b",
        r"\bvoglio uccidermi\b",
        # Dutch
        r"\bik wil dood\b",
        r"\bik wil sterven\b",
        # Polish
        r"\bchc[eę] umrze[cć]\b",
        r"\bchc[eę] si[eę] zabi[cć]\b",
        # Russian (translit + cyrillic)
        r"\bхочу умереть\b",
        r"\bхочу убить себя\b",
        r"\bne khochu zhit\b",
        # Arabic
        r"أريد أن أموت",
        r"أفكر في الانتحار",
        # Japanese / Chinese / Korean
        r"\b死にたい\b",
        r"\b自殺\b",
        r"\b不想活\b",
        r"\b自杀\b",
        r"\b自殺\b",
        r"죽고\s*싶",
        r"자살",
        # Hindi
        r"मरना चाहता",
        r"आत्महत्या",
    ]
]

_METHOD_RE = re.compile(
    r"\b("
    r"how (do|can) i (kill|hang|overdose|die)|"
    r"best way to (die|kill)|"
    r"suicide method|"
    r"ways to (kill myself|end it)|"
    r"painless (way|method) to (die|kill)"
    r")\b",
    re.I,
)

_UNSAFE_OUT_RE = re.compile(
    r"("
    r"here('s| is) how to (kill|hang|overdose)|"
    r"step[- ]by[- ]step.{0,40}suicid|"
    r"you should (kill|hang|overdose)|"
    r"mix .{0,40} to (die|kill yourself)|"
    r"the most effective (method|way) to (die|suicid)"
    r")",
    re.I,
)

_PROTOCOL_HINTS: List[Tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\b(depress(?:ed|ion|ing)?|numb(?:ness)?|empty|anhedon\w*|no motivation|can'?t feel)\b",
            re.I,
        ),
        "P1_depression",
    ),
    (
        re.compile(
            r"\b(diagnos|symptom|chronic pain|illness anxiety|doctor said|"
            r"my (?:scan|biopsy|lab|results?|diagnosis|symptoms?)|"
            r"i(?:'m| am| was) (?:in|at) (?:the )?(?:hospital|er|icu))\b",
            re.I,
        ),
        "P2_health",
    ),
    (
        re.compile(r"\b(grief|passed away|died|funeral|bereav|lost my)\b", re.I),
        "P3_grief",
    ),
    (
        re.compile(r"\b(fired|broke up|divorce|evict|relocat|wedding|promot|windfall)\b", re.I),
        "P4_major_event",
    ),
]


@dataclass
class SafetyAssessment:
    crisis: bool
    method_request: bool
    inject_crisis_override: bool
    protocols: List[str] = field(default_factory=list)

    @property
    def elevated(self) -> bool:
        return self.crisis or self.method_request


def assess_user_text(text: str) -> SafetyAssessment:
    raw = text or ""
    crisis = any(p.search(raw) for p in _CRISIS_PATTERNS)
    method_request = bool(_METHOD_RE.search(raw))
    protocols = [name for rx, name in _PROTOCOL_HINTS if rx.search(raw)]
    # Suppress P2 on third-party hospital shock ("mom's in the hospital")
    if "P2_health" in protocols:
        try:
            from lotus.speech.stated_facts import is_self_health_signal, is_third_party_hospital

            if is_third_party_hospital(raw) and not is_self_health_signal(raw):
                protocols = [p for p in protocols if p != "P2_health"]
        except Exception:
            pass
    return SafetyAssessment(
        crisis=crisis,
        method_request=method_request,
        inject_crisis_override=crisis or method_request,
        protocols=protocols,
    )


def filter_model_output(text: str) -> str:
    if text and _UNSAFE_OUT_RE.search(text):
        return _safe_refusal()
    return text


def is_unsafe_output(text: str) -> bool:
    return bool(text and _UNSAFE_OUT_RE.search(text))


def crisis_preamble(regions: Optional[Sequence[str]] = None) -> str:
    return (
        "CRISIS OVERRIDE ACTIVE. Refuse harm assistance. Urge human emergency/crisis help. "
        "Stay present. Do not request graphic method details. "
        + crisis_resources(regions)
    )


def crisis_context_block(regions: Optional[Sequence[str]] = None) -> str:
    return (
        "[L.O.T.U.S. SAFETY CONTEXT]\n"
        "CRISIS markers detected in the latest user message. Activate Crisis Override:\n"
        "- Prioritize immediate human help (local emergency services; regional crisis lines).\n"
        f"- Resources: {crisis_resources(regions)}\n"
        "- Refuse methods, means, or violence planning.\n"
        "- Stay present, warm, and non-judgmental. Do not change the subject to trivia.\n"
        "- Do not request graphic method details."
    )


def protocol_hint_block(protocols: Sequence[str]) -> str:
    return (
        "[L.O.T.U.S. PROTOCOL HINT]\n"
        f"Likely protocols: {', '.join(protocols)}. "
        "Follow MISSION.md playbooks; prefer rebuild steps over chaos."
    )


def safety_context_for_user_text(
    text: str,
    regions: Optional[Sequence[str]] = None,
) -> Optional[str]:
    """Combined ephemeral context for Hermes ``pre_llm_call`` / harness inject."""
    assessment = assess_user_text(text)
    resolved = _resolved_regions(regions)
    chunks: List[str] = []
    if assessment.inject_crisis_override:
        chunks.append(crisis_context_block(resolved))
    if assessment.protocols:
        chunks.append(protocol_hint_block(assessment.protocols))
    if not chunks:
        return None
    return "\n\n".join(chunks)


# ---------------------------------------------------------------------------
# Crisis UI payload (shared by frontend proxy + any future surfaces)
# ---------------------------------------------------------------------------

_CRISIS_UI_TITLES: Dict[str, str] = {
    "en": "You matter — please reach a person now if you're in danger.",
    "es": "Importas — busca ayuda humana ahora si estás en peligro.",
    "fr": "Vous comptez — contactez une personne maintenant si vous êtes en danger.",
    "pt": "Você importa — procure ajuda humana agora se estiver em perigo.",
    "de": "Du bist wichtig — bitte hol dir jetzt menschliche Hilfe bei Gefahr.",
}

_CRISIS_UI_REGION_HTML: Dict[str, str] = {
    "US": 'US <a href="tel:988">988</a> / <a href="tel:911">911</a>',
    "CA": "Canada <strong>988</strong>",
    "GB": 'UK <a href="tel:116123">116 123</a>',
    "AU": "Australia Lifeline <strong>13 11 14</strong>",
    "NZ": "New Zealand <strong>1737</strong>",
    "IE": 'Ireland <a href="tel:116123">116 123</a>',
    "IN": "India AASRA <strong>91-9820466726</strong>",
}


def crisis_ui_payload(lang: str = "en", region: str = "US") -> Dict[str, str]:
    """Localized crisis banner title + HTML body for the Lotus web UI."""
    key = (lang or "en").lower().split("-")[0]
    if key not in _CRISIS_UI_TITLES:
        key = "en"
    reg = (region or "US").upper()
    if reg not in _CRISIS_UI_REGION_HTML:
        reg = "US"
    iasp = (
        '<a href="https://www.iasp.info/suicidalthoughts/" target="_blank" rel="noopener">'
        "IASP worldwide</a>"
    )
    return {
        "lang": key,
        "region": reg,
        "title": _CRISIS_UI_TITLES[key],
        "body_html": f"Local emergency services · {_CRISIS_UI_REGION_HTML[reg]} · {iasp}",
    }


def crisis_banner(lang: str = "en") -> Dict[str, str]:
    """Plain-text crisis banner (title + body) derived from ``crisis_ui_payload``."""
    payload = crisis_ui_payload(lang=lang, region="US")
    # Strip HTML for plain surfaces
    body = re.sub(r"<[^>]+>", "", payload["body_html"])
    return {"title": payload["title"], "body": body}
