from lotus.speech import build_speech_care_directive
from lotus.speech.humanity import humanity_block
from lotus.speech.moment_route import detect_topic, route_moment


def test_humanity_mentions_openmed_and_not_911():
    text = humanity_block()
    assert "HUMANITY" in text
    assert "not 911" in text.lower() or "NOT 911" in text
    assert "diagnos" in text.lower()


def test_medical_emergency_routes_dispatch_calm():
    text = (
        "He's on the floor not waking up. I called 911. Lips look blue. "
        "Should I give him water?"
    )
    assert detect_topic(text) == "medical_emergency"
    route = route_moment(text)
    assert route.talk_mode == "dispatch_calm"
    assert route.max_sentences <= 4


def test_speech_includes_humanity_and_dispatch():
    text = build_speech_care_directive(
        user_text="Unresponsive on the floor. 911 coming. What do I do right now?",
        affect="mixed",
    )
    assert "GATEWAY" in text or "CHARACTER" in text or "ACUTE" in text
    assert "DISPATCH CALM" in text or "dispatch_calm" in text or "MOMENT ROUTE" in text
