from lotus.speech import build_speech_care_directive
from lotus.speech.ei import ei_block, perceive_emotions, understand_emotions


def test_perceive_grief_blends():
    primary, blends, intensity = perceive_emotions(
        "My husband died. I almost hate him for leaving and feel guilty.",
        protocols=["P3_grief"],
    )
    assert primary == "grief"
    assert "anger" in blends or "guilt" in blends


def test_understand_hate_for_leaving():
    primary, blends, _ = perceive_emotions(
        "Do you think it's wrong that some days I almost hate him for leaving?",
        protocols=["P3_grief"],
    )
    reading = understand_emotions(
        "Do you think it's wrong that some days I almost hate him for leaving?",
        primary=primary,
        blends=blends,
        protocols=["P3_grief"],
    )
    assert "not wrong" in reading.wisdom_move.lower() or "Answer the moral" in reading.wisdom_move
    assert "anger" in reading.logic.lower() or "fury" in reading.logic.lower()


def test_ei_block_has_perceive_understand_response():
    text = ei_block(
        "His side of the bed is still his. Someone said at least he's not suffering.",
        protocols=["P3_grief"],
        affect="low",
    )
    assert "PERCEIVE:" in text
    assert "UNDERSTAND" in text
    assert "WISE MOVE" in text
    assert "natural flow" in text.lower() or "talk like a person" in text.lower()


def test_speech_directive_uses_gateway():
    text = build_speech_care_directive(
        user_text="I'm scared I'll forget his voice.",
        protocols=["P3_grief"],
        affect="low",
    )
    assert "GATEWAY" in text or "CHARACTER" in text
    assert "--- profile:" not in text
