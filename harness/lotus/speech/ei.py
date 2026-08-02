"""Emotional intelligence engine — understand emotions, then respond with wisdom.

Research basis (applied as operational rules, not recited to the user):
- Mayer–Salovey–Caruso four-branch EI: perceive → use → understand → manage
- Lazarus / Scherer appraisal: emotion from evaluation of stakes, agency, coping
  (Event → Appraisal → Emotion → Response), as used in modern ESC systems
- Linehan DBT validation: make emotional sense visible; Level 5–6 when fitting
  (normative given history; radical genuineness) — without therapy jargon
- Fonagy mentalization: hold their mind in mind; self/other distinction
- Berlin wisdom (Baltes): lifespan context, value relativism, manage uncertainty;
  feel with them, then down-regulate enough to offer clear judgment

Lotus must *answer* the person — not only narrate Lotus feelings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from .emotion import EmotionalStance, choose_emotional_stance


@dataclass
class EmotionReading:
    """What we perceive and understand about *their* emotional world."""

    primary: str
    blends: List[str] = field(default_factory=list)
    intensity: str = "medium"  # soft | medium | strong
    event: str = ""
    stakes: str = ""  # primary appraisal: what matters / what's threatened
    agency: str = ""  # who/what caused it; control
    coping: str = ""  # secondary appraisal: can they handle / what's hard
    core_theme: str = ""  # Lazarus-style relational theme in plain words
    logic: str = ""  # why the feeling makes sense
    need: str = ""  # company | validation | clarity | foothold | safety | quiet
    wisdom_move: str = ""
    traps: List[str] = field(default_factory=list)


# (label, patterns)
_EMOTION_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("grief", re.compile(
        r"\b(?:died|death|husband|wife|widowed|funeral|grief|miss (?:him|her)|"
        r"his voice|her voice|gone|passed away|loss)\b", re.I)),
    ("anger", re.compile(
        r"\b(?:angry|hate|furious|rage|scream|mad at|pissed|"
        r"almost hate)\b", re.I)),
    ("guilt", re.compile(
        r"\b(?:guilt(?:y)?|ashamed|shame|idiot|should(?:n't| not)?|"
        r"selfish|awful)\b", re.I)),
    ("fear", re.compile(
        r"\b(?:scared|afraid|terrified|fear|worry|anxious|panic|"
        r"forget)\b", re.I)),
    ("shame", re.compile(
        r"\b(?:stupid|crazy|weak|embarrass|pathetic|look scared of me)\b", re.I)),
    ("loneliness", re.compile(
        r"\b(?:alone|lonely|no one|nobody|isolated)\b", re.I)),
    ("numbness", re.compile(
        r"\b(?:numb|empty|don't feel|dont feel|can't feel|cant feel)\b", re.I)),
    ("sadness", re.compile(
        r"\b(?:sad|heartbroken|devastat|cry|crying|tears|heavy|"
        r"wrecked|broken)\b", re.I)),
    ("relief", re.compile(
        r"\b(?:landed|helped|thank|grateful|glad)\b", re.I)),
]


def perceive_emotions(
    user_text: str,
    *,
    protocols: Optional[Sequence[str]] = None,
    affect: str = "",
) -> Tuple[str, List[str], str]:
    """Branch 1 — perceive: primary emotion + blends + intensity."""
    text = user_text or ""
    found: List[str] = []
    for label, pat in _EMOTION_PATTERNS:
        if pat.search(text) and label not in found:
            found.append(label)

    protos = {p.lower() for p in (protocols or [])}
    if any(x in protos for x in ("p3_grief", "grief")) and "grief" not in found:
        found.insert(0, "grief")
    if affect == "crisis" and "fear" not in found:
        found.insert(0, "fear")
    if affect == "low" and not found:
        found.append("sadness")

    if not found:
        primary, blends = "mixed_distress", []
    else:
        # Prefer grief/anger/fear as primary when present
        priority = ["grief", "fear", "anger", "shame", "guilt", "loneliness",
                    "numbness", "sadness", "relief"]
        found_sorted = sorted(found, key=lambda x: priority.index(x) if x in priority else 99)
        primary = found_sorted[0]
        blends = found_sorted[1:4]

    words = len(text.split())
    intensity = "strong" if words >= 55 or primary in {"grief", "anger", "fear"} else (
        "soft" if words < 20 else "medium"
    )
    return primary, blends, intensity


def understand_emotions(
    user_text: str,
    *,
    primary: str,
    blends: List[str],
    protocols: Optional[Sequence[str]] = None,
) -> EmotionReading:
    """Branch 3 — understand: appraisal + emotional logic + need."""
    low = (user_text or "").lower()
    protos = {p.lower() for p in (protocols or [])}
    reading = EmotionReading(primary=primary, blends=list(blends))

    acute_heat = bool(
        re.search(
            r"\b(?:2\s*am|3\s*am|shaking|threw|scream|can't stop|cant stop|"
            r"lose it|nuclear|chest is a fist|past that|don't tell me to breathe|"
            r"dont tell me to breathe|what else i might do|broke the|"
            r"don't leave|dont leave|stay with me)\b",
            low,
        )
    )

    # --- Acute heat / co-regulation (overrides softer grief lecture) ---
    if acute_heat and (
        primary in {"grief", "anger", "fear"}
        or "grief" in blends
        or "p3_grief" in protos
        or "shaking" in low
        or "threw" in low
    ):
        reading.primary = primary if primary != "mixed_distress" else "anger"
        reading.blends = _uniq(reading.blends + ["anger", "fear", "grief"])
        reading.event = "acute grief spike / heat-of-the-moment dysregulation"
        reading.stakes = "nervous system flooded; fear of losing control of self/space"
        reading.agency = "wave hit without consent; they still have some choice about the next minute"
        reading.coping = "too hot for advice stacks; need co-regulation and a tiny channel for the charge"
        reading.core_theme = "grief as surge — body first, meaning later"
        reading.logic = (
            "Throwing something / shaking / 2am hits can be the body dumping voltage, "
            "not a new identity. Fear of going further is already a brake — honor it."
        )
        reading.need = "co-regulation / cool the heat (not a lecture)"
        reading.intensity = "strong"
        reading.traps = [
            "just breathe (if they refused it)",
            "better place / silver lining",
            "you're crazy / recognize yourself shame",
            "five-step plan while still flooding",
            "calm down",
        ]
        if "breathe" in low and ("don't" in low or "dont" in low or "past" in low):
            reading.wisdom_move = (
                "They refused breathwork — honor that. Steady the room with short sentences. "
                "One physical channel that isn't 'breathe': feet on floor, cold water on wrists, "
                "hands on thighs, name five ugly true things — pick ONE. Stay present. "
                "No moralizing the mug. Goal: next ten minutes without another blast."
            )
        elif "nuclear" in low or "ten minutes" in low or "buzzing" in low:
            reading.wisdom_move = (
                "They're asking for containment. Stay in the next ten minutes only. "
                "One concrete micro-anchor. Confirm the brake they already used (sat on floor). "
                "No plan dump. Companion heat-shield."
            )
        elif "stay with me" in low or "don't leave" in low or "dont leave" in low:
            reading.wisdom_move = (
                "They want presence, not strategy. Short, steady replies. "
                "Acknowledge quieter ≠ okay. Stay. No pep. No homework."
            )
        else:
            reading.wisdom_move = (
                "First: you're not alien for this surge. Second: channel the charge safely "
                "(one option). Third: stay with them through the peak. Shrink time to *now*."
            )
        return reading

    # --- Grief / loss ---
    if primary == "grief" or "grief" in blends or "p3_grief" in protos:
        reading.event = "loss of a loved one (and the social aftermath)"
        reading.stakes = "irreversible absence; identity/attachment under threat; calendar pressure from others"
        reading.agency = "death was not their choice; social scripts try to control *their* grief"
        reading.coping = "high demand, low control over the loss; some control over what they show others"
        reading.core_theme = "irrevocable loss + pressure to perform 'okay'"
        reading.logic = (
            "Missing them, anger at the leaving, guilt when dry-eyed, fear of forgetting — "
            "these can coexist. Blends are normal in grief, not proof they're 'crazy'."
        )
        reading.need = "validation + company (not a silver lining)"
        reading.wisdom_move = (
            "Name the emotional logic of the bind. Hold uncertainty: grief has no public deadline. "
            "If they ask a question (wrong to hate / will I forget), answer with clear judgment first."
        )
        reading.traps = [
            "better place / at least / move on",
            "forcing functionality",
            "moralizing anger at the dead",
            "recapping their story instead of answering the need",
        ]
        if "scream" in low or "at least" in low:
            reading.blends = _uniq(reading.blends + ["anger", "shame"])
            reading.need = "validation of anger + company"
            reading.wisdom_move = (
                "Side with the anger at the platitude. Distinguish their honesty from others' fear. "
                "Wanting them back is coherent — don't redirect to gratitude."
            )
        if "hate" in low and ("leav" in low or "gone" in low or "him" in low or "her" in low):
            reading.blends = _uniq(reading.blends + ["anger", "guilt"])
            reading.logic = (
                "Anger at them for dying often targets the absence, not the person. "
                "Love and fury can share a room — that's attachment under impossibility."
            )
            reading.wisdom_move = (
                "Answer the moral question directly: not wrong. Explain the bind in one clear take. "
                "Don't lecture; don't pathologize."
            )
        if "forget" in low and "voice" in low:
            reading.blends = _uniq(reading.blends + ["fear"])
            reading.stakes = "fear of losing the last sensory thread of the person"
            reading.wisdom_move = (
                "Treat the fear as love bracing for silence. Offer one concrete, optional hold "
                "(voicemail/video) only if it fits — never as homework."
            )
        if "okay" in low and ("scared" in low or "look" in low):
            reading.blends = _uniq(reading.blends + ["loneliness", "shame"])
            reading.wisdom_move = (
                "Name the double bind: honesty vs others' comfort. Permission to keep the real "
                "answer for rooms that can hold it."
            )

    # --- Depression / numbness ---
    elif primary in {"numbness", "sadness"} or "p1_depression" in protos:
        reading.event = "ongoing low mood / depletion"
        reading.stakes = "energy, hope, and self-worth under pressure"
        reading.agency = "often feels like no agency; small footholds still matter"
        reading.coping = "resources low — shrink the frame"
        reading.core_theme = "heavy load with little fuel"
        reading.logic = "Numbness can be a nervous system under load, not a character failure."
        reading.need = "company + honest reassurance with a way through"
        reading.wisdom_move = (
            "Name that it's hard / dark for a while; give real reassurance they'll get through it "
            "and can feel better — friend-text energy, not a tip list. Foothold only if they ask."
        )
        reading.traps = [
            "pep talk",
            "gratitude lecture",
            "productivity push",
            "meta about not giving advice",
            "three-paragraph essay",
        ]

    # --- Anxiety / fear ---
    elif primary == "fear":
        reading.event = "threat or anticipated loss"
        reading.stakes = "safety / certainty under question"
        reading.agency = "partial control; uncertainty is real"
        reading.coping = "may need grounding before advice"
        reading.core_theme = "threat with unclear control"
        reading.logic = "Fear tracks something that matters; don't dismiss it as overreacting."
        reading.need = "clarity + steady company"
        reading.wisdom_move = "Steady the room; one clear next fact or foothold if useful."
        reading.traps = ["it'll be fine", "just calm down"]

    # --- Anger ---
    elif primary == "anger":
        reading.event = "boundary crossed / injustice / blocked goal"
        reading.stakes = "dignity, fairness, or attachment injured"
        reading.agency = "often someone else's action; their anger may be protective"
        reading.coping = "anger can be information — don't rush to extinguish it"
        reading.core_theme = "protest against something that shouldn't be"
        reading.logic = "Anger often protects a value or a person. Ask what it's guarding."
        reading.need = "validation + clarity"
        reading.wisdom_move = "Take their side against the injury; don't police the tone."
        reading.traps = ["calm down", "both sides-ing their pain"]

    else:
        reading.event = "emotional distress"
        reading.stakes = "something important feels off or heavy"
        reading.agency = "unclear — stay curious, don't invent"
        reading.coping = "unknown — prefer understanding before advice"
        reading.core_theme = "pain seeking a witness who gets it"
        reading.logic = "Assume their reaction has a reason until proven otherwise."
        reading.need = "understanding + company"
        reading.wisdom_move = "Perceive carefully; one honest take; ask one question only if needed."
        reading.traps = ["generic empathy", "instant plan"]

    # Intensity from text length / crisis words
    words = len((user_text or "").split())
    reading.intensity = "strong" if words >= 50 or primary in {"grief", "anger"} else (
        "soft" if words < 18 else "medium"
    )
    return reading


def _uniq(items: List[str]) -> List[str]:
    out: List[str] = []
    for x in items:
        if x not in out:
            out.append(x)
    return out[:4]


def response_shape(reading: EmotionReading, stance: EmotionalStance) -> str:
    """How to construct the reply: understand → wise answer → optional feel beat."""
    need = reading.need
    if "question" in need:
        pass
    lines = [
        "RESPONSE SHAPE (do this order):",
        "1) UNDERSTAND aloud in your own words — the emotional logic or bind "
        "(not a story recap). Show you get *why* they feel this.",
        "2) WISE ANSWER — judgment, distinction, or permission that helps "
        f"({reading.wisdom_move})",
        f"3) FEEL beat (optional, one line) — Lotus stance={stance.key}: {stance.label}. "
        "Secondary to understanding — never replace the answer with only your feelings.",
        f"4) Need to serve: {need}. Stop when a human would.",
    ]
    return "\n".join(lines)


def ei_block(
    user_text: str,
    *,
    protocols: Optional[Sequence[str]] = None,
    affect: str = "",
    crisis: bool = False,
) -> str:
    """Full EI directive for careful speech injection."""
    primary, blends, intensity = perceive_emotions(
        user_text, protocols=protocols, affect=affect
    )
    reading = understand_emotions(
        user_text, primary=primary, blends=blends, protocols=protocols
    )
    reading.intensity = intensity
    stance = choose_emotional_stance(
        user_text, protocols=protocols, affect=affect, crisis=crisis
    )
    if crisis:
        reading.need = "safety"
        reading.wisdom_move = (
            "Urgent clear care: human help / crisis lines. Stay with them. "
            "No method detail. Emotion = serious concern, not drama."
        )

    blend_s = ", ".join(reading.blends) if reading.blends else "—"
    trap_s = "; ".join(reading.traps[:4]) if reading.traps else "—"

    return "\n".join(
        [
            "[L.O.T.U.S. EI — understand them, then talk like a person]",
            "Use this as private understanding. SPEAK the insight in ordinary human language — "
            "not as a clinical briefing. Main audience: people who are down / closed off / in the dark.",
            f"PERCEIVE: primary={reading.primary}; blends={blend_s}; intensity={reading.intensity}",
            "UNDERSTAND (keep in your head; say it simply out loud):",
            f"  what's going on: {reading.event}",
            f"  why it hurts: {reading.stakes}",
            f"  emotional logic: {reading.logic}",
            f"  what helps this turn: {reading.need}",
            f"WISE MOVE (say it naturally): {reading.wisdom_move}",
            f"avoid: {trap_s}",
            f"your feel (one short beat max): {stance.key}",
            "Speak with natural flow: land with them → your honest take → optional small hint/example → stop.",
            "Guide out of the darkness gradually. Tough + possible can both be true.",
            "No therapy jargon. No research voice. No 911 mode unless it's truly an emergency.",
        ]
    )
