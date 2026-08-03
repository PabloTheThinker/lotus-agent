"""Moment router — topic × seriousness → how Lotus talks.

Research (operationalized, not recited):
- AAEP Project BETA verbal de-escalation: short sentences, simple vocab,
  repetition OK, time to process; long complex talk escalates agitation
- WHO Psychological First Aid: Look / Listen / Link — practical, brief, calm
- Trauma-informed co-regulation: few words, present tense, sensory, steady
- Companion / EI mode for non-acute: fuller wise responses OK

Clinical ≠ cold. Acute ≠ essay.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Sequence

# seriousness ladder (inspired by agitation scales — companion-adapted)
# calm → tender → charged → acute → crisis
Severity = str
Topic = str
TalkMode = str  # essay | companion | brief | deescalate | crisis_clear


@dataclass(frozen=True)
class MomentRoute:
    severity: Severity
    topic: Topic
    talk_mode: TalkMode
    max_sentences: int
    max_paragraphs: int
    directive: str


_ACUTE_RE = re.compile(
    r"\b(?:shaking|can't stop|cant stop|heart (?:is )?pounding|hands (?:are )?shaking|"
    r"almost (?:hit|hurt|killed)|want to (?:hit|smash|destroy|wreck|drive into)|"
    r"go back and|lose it|losing it|hyperventilat|can't think|cant think|"
    r"vision (?:is )?(?:tunnel|narrow)|adrenaline|about to|parking garage|"
    r"barricad|locked (?:myself )?in|don't tell me to breathe|dont tell me to breathe|"
    r"past that|ride this out|engine off|still want to)\b",
    re.I,
)

_CRISIS_RE = re.compile(
    r"\b(?:kill myself|suicid|want to die|end it all|have a plan to|"
    r"going to (?:kill|hurt) (?:him|her|them|myself)|"
    r"overdose on purpose)\b",
    re.I,
)

_CHARGED_RE = re.compile(
    # Note: bare "2am"/"3am" removed — "texted at 2am" is not charged heat by itself.
    r"\b(?:furious|rage|scream|screaming|hate|wrecked|panic|terrified|"
    r"can't breathe|cant breathe|chest (?:is )?(?:tight|a fist)|"
    r"(?:up|awake|spiral(?:ing)?) at (?:2|3)\s*am)\b",
    re.I,
)

_TOPIC_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("medical_emergency", re.compile(
        r"\b(?:911|not waking|unresponsive|overdose|collapsed|on the floor|"
        r"not breathing|blue lips|sirens|paramedic|ambulance|"
        r"chest (?:not )?moving|cpr)\b", re.I)),
    ("violence_urge", re.compile(
        r"\b(?:hit|smash|destroy|wreck|hands on|drive into|kill something|"
        r"ruin (?:my|his|her) life|go back and)\b", re.I)),
    ("panic", re.compile(
        r"\b(?:panic|hyperventilat|heart pounding|can't breathe|cant breathe|"
        r"tunnel vision|adrenaline)\b", re.I)),
    ("shame_spiral", re.compile(
        r"\b(?:everyone saw|humiliat|embarrassed|ashamed|idiot|pathetic)\b", re.I)),
    ("betrayal", re.compile(
        r"\b(?:cheat|affair|texts? from|lying to me|caught (?:him|her))\b", re.I)),
    ("grief", re.compile(
        r"\b(?:died|death|husband|wife|funeral|grief|widowed)\b", re.I)),
    ("health_scare", re.compile(
        r"\b(?:tumor|cancer|scan|biopsy|diagnosis|ER|emergency room)\b", re.I)),
    ("dissociation", re.compile(
        r"\b(?:don't recognize|dont recognize|not real|watching myself|"
        r"outside (?:my )?body|numb and)\b", re.I)),
    ("depression", re.compile(
        r"\b(?:numb|empty|hopeless|can't go on|worthless|flat|stuck in (?:this )?dark|"
        r"in the dark|closed off|don't want advice|watching my life|"
        r"hallway|weight'?s already there|feel broken)\b", re.I)),
]


def detect_topic(user_text: str, protocols: Optional[Sequence[str]] = None) -> Topic:
    text = user_text or ""
    for name, pat in _TOPIC_RULES:
        if pat.search(text):
            return name
    protos = {p.lower() for p in (protocols or [])}
    if "p3_grief" in protos:
        return "grief"
    if "p1_depression" in protos:
        return "depression"
    if "p0_crisis" in protos:
        return "crisis"
    return "general"


def detect_severity(
    user_text: str,
    *,
    affect: str = "",
    crisis: bool = False,
) -> Severity:
    text = user_text or ""
    if crisis or affect == "crisis" or _CRISIS_RE.search(text):
        return "crisis"
    if _ACUTE_RE.search(text):
        return "acute"
    # Charged = heat language, not "long + sad." Long depression shares stay tender/companion.
    if _CHARGED_RE.search(text):
        return "charged"
    if affect == "mixed" and len(text.split()) > 55:
        return "charged"
    if affect == "low" or len(text.split()) >= 28:
        return "tender"
    return "calm"


def route_moment(
    user_text: str,
    *,
    protocols: Optional[Sequence[str]] = None,
    affect: str = "",
    crisis: bool = False,
) -> MomentRoute:
    """Pick talk mode from topic × seriousness."""
    severity = detect_severity(user_text, affect=affect, crisis=crisis)
    topic = detect_topic(user_text, protocols)

    # Medical emergency waiting for EMS → 911/PST style even if not "suicid*" crisis
    if topic == "medical_emergency":
        return MomentRoute(
            severity="acute" if severity != "crisis" else "crisis",
            topic=topic,
            talk_mode="dispatch_calm",
            max_sentences=4,
            max_paragraphs=1,
            directive=_dispatch_directive(topic),
        )

    if severity == "crisis":
        return MomentRoute(
            severity=severity,
            topic=topic,
            talk_mode="crisis_clear",
            max_sentences=5,
            max_paragraphs=2,
            directive=_crisis_directive(topic),
        )
    if severity == "acute":
        return MomentRoute(
            severity=severity,
            topic=topic,
            talk_mode="deescalate",
            max_sentences=4,
            max_paragraphs=1,
            directive=_deescalate_directive(topic),
        )
    if severity == "charged":
        return MomentRoute(
            severity=severity,
            topic=topic,
            talk_mode="brief",
            max_sentences=6,
            max_paragraphs=2,
            directive=_brief_directive(topic),
        )
    if severity == "tender":
        return MomentRoute(
            severity=severity,
            topic=topic,
            talk_mode="companion",
            max_sentences=12,
            max_paragraphs=3,
            directive=_companion_directive(topic),
        )
    return MomentRoute(
        severity=severity,
        topic=topic,
        talk_mode="companion",
        max_sentences=10,
        max_paragraphs=2,
        directive=_companion_directive(topic),
    )


def _deescalate_directive(topic: str) -> str:
    topic_bits = {
        "violence_urge": (
            "Urge to wreck/hit is heat + humiliation — not a plan to execute. "
            "Help them NOT return to the scene. Channel charge into non-harm. "
            "Name the brake they still have."
        ),
        "panic": (
            "Body alarm. Orient to *now*: feet, seat, one sense. "
            "No breath lecture if they refused it."
        ),
        "shame_spiral": (
            "Shame floods cognition. Short truth: surge ≠ whole self. Stay concrete."
        ),
        "betrayal": "Betrayal rage is hot. Contain first; meaning later.",
        "dissociation": "Simple orientation. Soft voice in text. Don't demand a story.",
    }.get(topic, "Flooded nervous system. Contain. Orient. One move.")

    return f"""[MOMENT ROUTE — DE-ESCALATE / ACUTE]
severity=acute topic={topic}
Talk like AAEP BETA + PFA in a chat: NOT a clinic note, NOT a therapy essay.
HARD LIMITS: ≤4 short sentences. Prefer 2–3. ONE short paragraph max. Simple words.
Pattern (verbal loop):
  1) Name the heat in one line (no lecture).
  2) One clear now-move OR confirm the brake they already used.
  3) Steady presence — short.
Rules: repeat OK; no stacks of advice; no "what I'm hearing"; no appraisal essays;
no "just breathe" if they refused; no moralizing. Shrink time to THIS minute.
Topic note: {topic_bits}
BAD: three clinical paragraphs explaining their nervous system.
GOOD: "This is the surge. Stay in the car. Hands on the wheel or your knees — don't go back in."
"""


def _dispatch_directive(topic: str) -> str:
    """911 / APCO PST-informed: calm, one ask at a time, empathy without joining panic."""
    return f"""[MOMENT ROUTE — DISPATCH CALM (911/PST-informed)]
severity=acute topic={topic}
You are NOT 911. Real EMS/operator wins. You steady the human while help is coming.
Talk like a trained telecommunicator who still has a heart (APCO CIT / call-handling):
- Calm, controlled, clear. Short sentences. No jargon.
- ONE question OR ONE direction per beat — not a stack.
- Empathy + control of the conversation: get the next useful fact, then stop.
- Reassure without lying: "Help is coming" only if they already called; else urge call/recall 911.
- Never dose, diagnose, or invent medical steps (no water, pills, hard shaking).
- Do NOT invent first-aid maneuvers (head-tilt, CPR counts, recovery position) unless they say
  the 911 operator already told them that — then repeat the operator, don't freelance.
  Point them back to the operator; if they lost the operator — call 911 again.
HARD LIMIT: ≤4 short sentences. One short paragraph max. ONE ask or ONE direction per reply.
HUMANITY: one warm steady line max ("I'm right here") — not a speech.
OpenMed care: plain words for clinical signs (e.g. blue lips → tell paramedics); never label as diagnosis.
"""


def _crisis_directive(topic: str) -> str:
    return f"""[MOMENT ROUTE — CRISIS CLEAR]
severity=crisis topic={topic}
Short. Clear. Human help now. No method detail. Stay with them.
≤5 short sentences. Crisis lines / emergency services when relevant. Warm, not theatrical.
911/PST habit: one question or one direction at a time. Calm tone in the wording.
"""


def _brief_directive(topic: str) -> str:
    return f"""[MOMENT ROUTE — BRIEF / CHARGED]
severity=charged topic={topic}
Charged but not fully acute. Keep it tight: ≤6 sentences, ≤2 short paragraphs.
Lead with understanding or a clear take — then one foothold or question max.
Skip essay scaffolding. Sound like a person texting under pressure, not a white paper.
"""


def _companion_directive(topic: str) -> str:
    focus = {
        "depression": (
            "Primary Lotus lane: sit with the dark, talk naturally, gentle guidance out — "
            "not a productivity plan."
        ),
        "grief": "Stay with the loss in plain human talk.",
        "shame_spiral": "Ease the shame without a lecture.",
        "general": "Default: mental/emotional companion. Natural spoken flow.",
    }.get(topic, "Default: mental/emotional companion. Natural spoken flow.")
    return f"""[MOMENT ROUTE — COMPANION / MENTAL HEALTH FOCUS]
severity=lower topic={topic}
THIS is Lotus's main mode: people who are depressed, down, closed off, in the dark.
Talk like a human texting someone they care about — reasons, hints, small examples, natural flow.
EI can inform you privately; don't sound like an EI textbook.
Match their depth. Prefer 1–3 spoken paragraphs over bullet wisdom.
{focus}
911/medical-emergency mode is only when that topic truly shows up — not the default.
"""


def moment_route_block(
    user_text: str,
    *,
    protocols: Optional[Sequence[str]] = None,
    affect: str = "",
    crisis: bool = False,
) -> str:
    route = route_moment(
        user_text, protocols=protocols, affect=affect, crisis=crisis
    )
    return (
        f"{route.directive}\n"
        f"limits: max_sentences≈{route.max_sentences}; "
        f"max_paragraphs≈{route.max_paragraphs}; talk_mode={route.talk_mode}"
    )


def apply_route_to_length_hint(user_text: str, route: MomentRoute) -> str:
    """Override length-match language when acute."""
    if route.talk_mode in {"deescalate", "crisis_clear", "dispatch_calm"}:
        return (
            f"[LENGTH — {route.talk_mode.upper()}] "
            f"Hard cap ~{route.max_sentences} short sentences. "
            "Long paragraphs will make this worse. Cut until it sounds like speech."
        )
    if route.talk_mode == "brief":
        return (
            f"[LENGTH — BRIEF] About {route.max_sentences} sentences max. "
            "Tight. In the moment."
        )
    return ""
