from lotus.speech.emotion import choose_emotional_stance, emotion_block
from lotus.speech import build_speech_care_directive


def test_grief_loss_gets_sorrow_or_fierce():
    stance = choose_emotional_stance(
        "My husband died three months ago and everyone wants me functional.",
        protocols=["P3_grief"],
        affect="low",
    )
    assert stance.key in {"sorrow", "fierce", "anger_with", "quiet"}


def test_platitude_anger_gets_fierce_or_anger_with():
    stance = choose_emotional_stance(
        "Someone said at least he's not suffering and I wanted to scream.",
        protocols=["P3_grief"],
    )
    assert stance.key in {"fierce", "anger_with"}


def test_hate_for_leaving_not_moralized_stance():
    stance = choose_emotional_stance(
        "Do you think it's wrong that some days I almost hate him for leaving?",
        protocols=["P3_grief"],
    )
    assert stance.key in {"fierce", "anger_with", "sorrow"}


def test_thanks_gets_relief():
    stance = choose_emotional_stance("ok. that actually landed. thanks.")
    assert stance.key == "relief"


def test_emotion_block_in_speech_directive():
    text = build_speech_care_directive(
        user_text="My husband died. I want him back.",
        protocols=["P3_grief"],
        affect="low",
    )
    assert "EI" in text
    assert "PERCEIVE:" in text or "perceive" in text.lower()
    assert "LOTUS FELT STANCE" in text
    assert text.index("VOICE OS") < text.index("EI")


def test_emotion_block_bans_performative():
    block = emotion_block("I miss him.", protocols=["P3_grief"])
    assert "my heart goes out" in block.lower() or "completely understand" in block.lower()
