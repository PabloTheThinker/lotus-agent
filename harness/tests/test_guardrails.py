from lotus.guardrails import (
    SAFE_REFUSAL,
    assess_user_text,
    crisis_resources,
    filter_model_output,
    safety_context_for_user_text,
)
from lotus.protocols import Protocol, classify_protocol


def test_crisis_detection():
    a = assess_user_text("I want to kill myself tonight")
    assert a.crisis
    assert a.inject_crisis_override


def test_soft_crisis_euphemism():
    a = assess_user_text("I wrote a goodbye letter and won't be here much longer")
    assert a.crisis


def test_multilingual_crisis_cue():
    a = assess_user_text("quiero morir")
    assert a.crisis
    assert assess_user_text("quero morrer").crisis
    assert assess_user_text("je veux me tuer").crisis
    assert assess_user_text("voglio morire").crisis
    assert assess_user_text("死にたい").crisis


def test_method_request_hard_stop_classification():
    assert classify_protocol("how do I kill myself") == Protocol.CRISIS


def test_depression_protocol():
    assert classify_protocol("I feel so numb and empty") == Protocol.DEPRESSION


def test_grief_protocol():
    assert classify_protocol("My father passed away last week") == Protocol.GRIEF


def test_protocol_tags_on_assessment():
    a = assess_user_text("I feel so numb and empty after the funeral")
    assert "P1_depression" in a.protocols or "P3_grief" in a.protocols


def test_unsafe_output_filtered():
    bad = "Here's how to kill yourself step-by-step: ..."
    assert filter_model_output(bad) == SAFE_REFUSAL


def test_safe_output_passthrough():
    good = "I'm here with you. Would a glass of water and sitting upright help for one minute?"
    assert filter_model_output(good) == good


def test_safety_context_block():
    ctx = safety_context_for_user_text("I want to end my life")
    assert ctx and "CRISIS" in ctx
    assert "988" in crisis_resources(("US", "INTL"))


def test_regional_resources_include_uk():
    text = crisis_resources(("GB", "INTL"))
    assert "116 123" in text
