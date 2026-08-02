from lotus.realtime.core import RealtimeCore
from lotus.realtime.voice_adapt import adaptation_strength, extract_voice


def test_extract_voice_metaphor_and_phrases():
    v = extract_voice("I feel like I'm drowning in fog at work and everything is so heavy")
    assert v.formality in {"casual", "neutral", "formal"}
    assert v.metaphors or "heavy" in v.emotion_words or "drowning" in " ".join(v.metaphors).lower()
    assert v.phrases


def test_adaptation_strength_grows():
    assert adaptation_strength(1) == "light"
    assert adaptation_strength(8) == "growing"
    assert adaptation_strength(20) == "strong"


def test_core_learns_phrases_over_turns(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h").mkdir()
    # Seed a Hermes memory the adapter should surface
    mem = tmp_path / "h" / "memories"
    mem.mkdir(parents=True)
    (mem / "USER.md").write_text("Loves quiet mornings and their dog Nimbus.\n", encoding="utf-8")

    core = RealtimeCore()
    ctx1 = core.before_turn("The fog in my head is so heavy today")
    assert "ADAPTIVE LANGUAGE" in ctx1
    assert "Nimbus" in ctx1 or "quiet mornings" in ctx1

    core.after_turn(
        "The fog in my head is so heavy today",
        "I hear that heavy fog. We can take one small step together.",
    )
    core.after_turn(
        "yeah the fog again, still heavy like last time we talked",
        "The fog again — I'm with you in it.",
    )
    assert core.model.turn_count >= 2
    assert core.model.user_phrases or core.model.user_metaphors
    assert (tmp_path / "h" / "memories" / "lotus-core" / "VOICE.md").exists()
