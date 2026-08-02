from lotus.backends.cursor_cli import _compose_prompt
from lotus.speech import build_speech_care_directive, humanizer_block, turn_depth
from lotus.speech.humanizer import HUMANIZER_DIRECTIVE, length_match_directive


def test_humanizer_block_present():
    assert "HUMANIZER" in humanizer_block()
    assert "mirrored too hard" in HUMANIZER_DIRECTIVE.lower() or "not a polished echo" in HUMANIZER_DIRECTIVE.lower()
    assert "delve" in HUMANIZER_DIRECTIVE.lower() or "tapestry" in HUMANIZER_DIRECTIVE.lower()


def test_speech_directive_includes_humanizer():
    text = build_speech_care_directive(
        user_text="I feel numb",
        protocols=["P1_depression"],
        affect="low",
    )
    assert "GATEWAY" in text or "CHARACTER" in text
    assert "LENGTH:" in text


def test_invited_brutal_truth_asks_for_short_honesty():
    text = build_speech_care_directive(
        user_text="Be brutally honest with me — why am I stuck?",
        protocols=["P1_depression"],
        affect="low",
    )
    assert "TRUTH=invited" in text or "brutal" in text.lower()
    assert "raw" in text.lower() or "honest" in text.lower()


def test_long_user_message_gets_talk_plan_length():
    long = (
        "I've been waking up already tired for months. Work feels like I'm underwater. "
        "I used to call my sister but I stopped because I don't want to dump on her again. "
        "Some days I can almost pretend I'm fine and then something tiny breaks me open. "
        "I don't want a pep talk. I want someone to actually sit with how heavy this is "
        "and not rush me into a five-step plan I won't keep."
    )
    assert turn_depth(long) == "long"
    directive = length_match_directive(long)
    assert "LONG" in directive
    speech = build_speech_care_directive(
        user_text=long,
        protocols=["P1_depression"],
        affect="low",
    )
    assert "GATEWAY" in speech or "CHARACTER" in speech
    assert "LENGTH:" in speech


def test_cursor_compose_matches_long_share():
    long = " ".join(["I keep carrying this weight around and nobody sees it."] * 12)
    p = _compose_prompt(long, system_prompt="sys")
    assert "No X, no Y" in p or "no polish" in p.lower() or "own thought" in p
    assert "Long share" in p or "flowing paragraphs" in p
    short = _compose_prompt("hey", system_prompt="sys")
    assert "Keep it tight" in short or "real person" in short or "No X, no Y" in short
