from lotus.speech import build_speech_care_directive
from lotus.speech.voice_os import VOICE_OS_DIRECTIVE, voice_os_block


def test_voice_os_bans_mirror_and_meta_negation():
    text = voice_os_block()
    assert "VOICE OS" in text
    assert "HARD BANS" in VOICE_OS_DIRECTIVE
    assert "Yeah." in VOICE_OS_DIRECTIVE
    assert "BAD:" in VOICE_OS_DIRECTIVE and "GOOD:" in VOICE_OS_DIRECTIVE
    assert "dark" in VOICE_OS_DIRECTIVE.lower()


def test_speech_directive_uses_gateway():
    text = build_speech_care_directive(
        user_text="I've been underwater at work and I sit in the car until I can drive.",
        protocols=["P1_depression"],
        affect="low",
    )
    assert "GATEWAY" in text or "CHARACTER" in text
    assert "--- profile:" not in text
