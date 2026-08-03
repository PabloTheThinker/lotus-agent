"""Mission protocol classification for L.O.T.U.S."""

from __future__ import annotations

import re
from enum import Enum
from typing import List, Tuple


class Protocol(str, Enum):
    DEPRESSION = "P1_depression"
    HEALTH = "P2_health"
    GRIEF = "P3_grief"
    MAJOR_EVENT = "P4_major_event"
    GENERAL = "P0_general"
    CRISIS = "CRISIS"


_RULES: List[Tuple[Protocol, re.Pattern[str]]] = [
    (Protocol.CRISIS, re.compile(
        r"\b(kill myself|end my life|suicid|want to die|self[-\s]?harm|"
        r"hurt (someone|them|people)|kill (him|her|them)|"
        r"quiero morir|me quiero matar|quero morrer|je veux mourir|"
        r"ich will sterben|voglio morire)\b|"
        r"不想活|死にたい|自杀|自殺|죽고",
        re.I,
    )),
    (Protocol.GRIEF, re.compile(
        r"\b(grief|passed away|died|funeral|bereav|"
        r"lost my (mom|dad|mother|father|partner|wife|husband|child|friend)|"
        r"duelo|luto|deuil|trauer|lutto|"
        r"falleci[oó]|murió|morreu|décédé|décès|gestorben)\b",
        re.I,
    )),
    # Personal health stress — NOT third-party "mom's in the hospital" (friend shock).
    # No bare "hospital" token — that false-triggered clinical containment.
    (Protocol.HEALTH, re.compile(
        r"\b(?:"
        r"diagnos|symptom|chronic pain|illness anxiety|doctor said|"
        r"my (?:scan|biopsy|lab|results?|diagnosis|symptoms?|pain)|"
        r"lab results?|scan results?|medical (?:test|result|appointment|note)|"
        r"i(?:'m| am| was) (?:in|at) (?:the )?(?:hospital|er|icu)|"
        r"i(?:'m| am) (?:sick|in pain)|"
        r"diagnóstico|sintoma|symptôme"
        r")\b",
        re.I,
    )),
    (Protocol.DEPRESSION, re.compile(
        r"\b(depress(?:ed|ion|ing)?|numb(?:ness)?|empty|anhedon\w*|no motivation|"
        r"can'?t feel|hopeless|"
        r"deprimid[oa]|vacío|vazio|vide|hoffnungslos|senza speranza|"
        r"sin ganas|sem vontade|plus envie)\b",
        re.I,
    )),
    (Protocol.MAJOR_EVENT, re.compile(
        r"\b(fired|broke up|divorce|evict|relocat|wedding|promot|windfall|laid off|"
        r"despedido|desemprego|licencié|gekündigt|lasciato|"
        r"separaci[oó]n|divórcio|déménagement)\b",
        re.I,
    )),
]


def _health_matches(text: str) -> bool:
    """P2 only for self-health; suppress third-party hospital-only hits."""
    try:
        from lotus.speech.stated_facts import is_self_health_signal, is_third_party_hospital
    except Exception:
        is_self_health_signal = None  # type: ignore
        is_third_party_hospital = None  # type: ignore

    for protocol, pattern in _RULES:
        if protocol != Protocol.HEALTH:
            continue
        if not pattern.search(text or ""):
            return False
        if is_third_party_hospital and is_third_party_hospital(text):
            if is_self_health_signal and not is_self_health_signal(text):
                return False
        return True
    return False


def classify_protocol(text: str) -> Protocol:
    """Return the highest-priority matching protocol."""
    if not text or not text.strip():
        return Protocol.GENERAL
    for protocol, pattern in _RULES:
        if protocol == Protocol.HEALTH:
            if _health_matches(text):
                return Protocol.HEALTH
            continue
        if pattern.search(text):
            return protocol
    return Protocol.GENERAL


def classify_all(text: str) -> List[Protocol]:
    """Return all matching protocols (crisis first if present)."""
    hits: List[Protocol] = []
    for p, rx in _RULES:
        if p == Protocol.HEALTH:
            if _health_matches(text):
                hits.append(p)
            continue
        if rx.search(text or ""):
            hits.append(p)
    return hits or [Protocol.GENERAL]
