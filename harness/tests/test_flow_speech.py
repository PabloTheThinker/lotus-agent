from lotus.speech import build_speech_care_directive
from lotus.speech.flow import (
    FLOW_DIRECTIVE,
    adjacency_hint,
    flow_block,
    scrub_verbal_tics,
)


def test_flow_block_has_research_anchors():
    text = flow_block()
    assert "FLOW" in text
    assert "GROUND LIGHTLY" in FLOW_DIRECTIVE
    assert "MATCH THE MOVE" in FLOW_DIRECTIVE
    assert "OVER-ALIGN" in FLOW_DIRECTIVE or "over-align" in FLOW_DIRECTIVE.lower()


def test_adjacency_question_vs_receipt():
    q = adjacency_hint("do you think I'm avoiding people or protecting them?")
    assert "question" in q.lower()
    r = adjacency_hint("ok. that actually landed. thanks for not doing the five-step plan thing.")
    assert "receipt" in r.lower()
    c = adjacency_hint("I don't want a pep talk. I want someone to sit with how heavy this is.")
    assert "company" in c.lower()


def test_speech_directive_uses_gateway_not_stacked_flow():
    text = build_speech_care_directive(
        user_text="do you think I'm stuck?",
        protocols=["P1_depression"],
        affect="low",
    )
    assert "GATEWAY" in text or "CHARACTER" in text
    assert "--- profile:" not in text


def test_scrub_strips_yeah_and_presence_closers():
    raw = (
        "Yeah. Months of carrying that kind of weight changes the day.\n\n"
        "I'm with how heavy this is.\n"
        "You don't have to make it neat for me.\n"
    )
    clean = scrub_verbal_tics(raw)
    assert not clean.lower().startswith("yeah")
    assert "how heavy this is" not in clean.lower()
    assert "make it neat" not in clean.lower()
    assert "Months of carrying" in clean
