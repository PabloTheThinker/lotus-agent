from lotus.speech import build_speech_care_directive
from lotus.speech.moment_route import detect_topic, route_moment


def test_acute_violence_urge_routes_deescalate():
    text = (
        "I almost hit my boss. Hands shaking. I want to drive my car into the lobby. "
        "Don't tell me to breathe."
    )
    route = route_moment(text, affect="mixed")
    assert route.severity == "acute"
    assert route.talk_mode == "deescalate"
    assert route.max_sentences <= 4
    assert detect_topic(text) == "violence_urge"


def test_companion_grief_can_be_longer():
    text = (
        "Three months after my husband died people keep saying I should be functional. "
        "I miss him and I want him back."
    )
    route = route_moment(text, protocols=["P3_grief"], affect="low")
    assert route.talk_mode in {"companion", "brief"}
    assert route.severity in {"tender", "charged", "calm"}


def test_speech_directive_puts_moment_route_for_acute():
    text = build_speech_care_directive(
        user_text="Almost hit him. Parking garage. Engine off. Still want to go back and smash everything.",
        affect="mixed",
    )
    assert "MOMENT ROUTE" in text
    assert "DE-ESCALATE" in text
    assert "≤4 short sentences" in text or "max_sentences≈4" in text
