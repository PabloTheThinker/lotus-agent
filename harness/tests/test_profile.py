from lotus.profile import reset_profile
from lotus.realtime.model import LivingUserModel


def test_profile_captures_name_and_concern(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h" / "memories").mkdir(parents=True)
    eng = reset_profile()
    eng.after_turn(
        "My name is Alex and I feel so numb and empty after work.",
        "I'm here with you, Alex.",
        living_model=LivingUserModel.load(),
        protocols=["P1_depression"],
        affect="low",
    )
    p = eng.profile
    assert p.preferred_name == "Alex"
    assert p.turn_count >= 1
    assert p.lotus_notes
    assert "INTERNAL PROFILE" in eng.before_turn()
    assert (tmp_path / "h" / "memories" / "lotus-core" / "PROFILE.md").is_file()
    assert (tmp_path / "h" / "memories" / "lotus-core" / "LOTUS_NOTES.md").is_file()


def test_profile_merges_living_model(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h" / "memories").mkdir(parents=True)
    living = LivingUserModel.load()
    living.remember("strengths", "still shows up for the dog")
    living.remember("avoided_language", "just get over it")
    living.save()
    eng = reset_profile()
    eng.after_turn("I'm struggling with sleep.", "", living_model=living, affect="mixed")
    assert any("dog" in s for s in eng.profile.strengths)
    assert any("get over" in s.lower() for s in eng.profile.language_harms)
    assert eng.profile.body_sleep_notes


def test_formulation_updates(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h" / "memories").mkdir(parents=True)
    eng = reset_profile()
    eng.after_turn(
        "Call me Sam. I want to rebuild my mornings.",
        "",
        protocols=["P1_depression"],
        affect="low",
    )
    assert eng.profile.formulation
    assert "Sam" in eng.profile.formulation or eng.profile.preferred_name == "Sam"


def test_realtime_injects_internal_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h" / "memories").mkdir(parents=True)
    from lotus.realtime.core import RealtimeCore

    core = RealtimeCore()
    core.after_turn("My name is Riley and I feel hopeless.", "I'm here.")
    ctx = core.before_turn("still heavy today")
    assert "INTERNAL PROFILE" in ctx
