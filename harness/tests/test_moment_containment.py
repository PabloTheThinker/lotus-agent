"""Stated facts, context USE vs invent, health false-positive containment."""

from lotus.protocols import Protocol, classify_all, classify_protocol
from lotus.speech.context_lock import CONTEXT_LOCK
from lotus.speech.gateway import gateway_block
from lotus.speech.moment_route import detect_severity
from lotus.speech.patterns import TalkPatternMemory, build_talk_plan, recognize_hits
from lotus.speech.stated_facts import (
    extract_stated_facts,
    is_self_health_signal,
    is_third_party_hospital,
    moment_containment_directive,
)


def test_context_lock_allows_stated_use():
    assert "USE facts" in CONTEXT_LOCK or "USE" in CONTEXT_LOCK
    assert "unless THEY said it" in CONTEXT_LOCK or "unless they said it" in CONTEXT_LOCK.lower()
    assert "invent" in CONTEXT_LOCK.lower()


def test_extract_drunk_stated_fact():
    facts = extract_stated_facts(
        "i'm drunk and i texted my ex. i feel sick about it."
    )
    assert facts.intoxicated
    assert "drunk" in facts.tags
    assert any("drunk" in f for f in facts.facts)


def test_mom_hospital_is_third_party_not_self_health():
    text = "omg my mom's in the hospital. i just found out"
    assert is_third_party_hospital(text)
    assert not is_self_health_signal(text)
    assert classify_protocol(text) != Protocol.HEALTH
    assert Protocol.HEALTH not in classify_all(text)


def test_self_hospital_is_health():
    text = "i'm in the hospital waiting on scan results and i'm freaking out"
    assert is_self_health_signal(text)
    assert classify_protocol(text) == Protocol.HEALTH


def test_gateway_uses_stated_drunk_and_containment():
    text = gateway_block(
        "i'm drunk and i texted my ex at 2am. i already feel sick about it."
    )
    assert "MOMENT CONTAINMENT" in text
    assert "ACTIVE FACTS" in text
    assert "drunk" in text.lower()
    assert "USE these" in text or "USE" in text
    assert "INTOXICATION" in text


def test_gateway_mom_hospital_not_health_quiz():
    text = gateway_block("omg my mom's in the hospital. i just found out")
    assert "MOMENT CONTAINMENT" in text
    assert "friend-shock" in text.lower() or "NOT a clinical" in text
    assert "HEALTH CONTAINMENT" not in text or "third-party" in text.lower()


def test_health_containment_when_p2():
    text = moment_containment_directive(
        "my scan results came back and i can't stop spiraling",
        protocols=["P2_health"],
    )
    assert "HEALTH CONTAINMENT" in text
    assert "clinician-question" in text.lower() or "doctor-question" in text.lower()


def test_2am_text_not_charged_severity():
    # Bare 2am should not escalate severity by itself
    sev = detect_severity("i texted my ex at 2am and said stuff i shouldn't")
    assert sev not in {"acute", "crisis", "charged"}


def test_intoxicated_pattern_routes_company():
    hits = {h.name for h in recognize_hits("i'm drunk and sitting here alone")}
    assert "intoxicated" in hits
    plan = build_talk_plan(
        "i'm drunk and sitting here alone",
        memory=TalkPatternMemory(),
    )
    assert plan.need in {"company", "sit", "witness"}
