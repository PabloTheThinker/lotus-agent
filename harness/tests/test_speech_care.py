from lotus.speech import (
    brutal_truth_mode,
    build_speech_care_directive,
    extract_language_corrections,
    profiles_for,
)


def test_grief_profile_avoids_silver_linings():
    profiles = profiles_for(moment_kinds=["grief"], protocols=["P3_grief"], affect="low")
    assert profiles[0].key == "grief"
    joined = " ".join(profiles[0].avoid).lower()
    assert "better place" in joined or "move on" in joined


def test_brutal_truth_invited():
    assert brutal_truth_mode("Please don't sugarcoat it — tell me straight") == "invited"


def test_brutal_truth_required_for_emergency_language():
    assert brutal_truth_mode("I have crushing chest pain and can't breathe") == "required"


def test_brutal_truth_off_by_default():
    assert brutal_truth_mode("I feel heavy today") == "off"


def test_language_correction_extraction():
    hits = extract_language_corrections("Please don't say 'just get over it' to me")
    assert hits
    assert any("get over" in h.lower() or "just" in h.lower() for h in hits)


def test_directive_includes_profile_and_truth_mode():
    text = build_speech_care_directive(
        user_text="My father passed away and I don't want silver linings",
        moment_kinds=["grief"],
        protocols=["P3_grief"],
        affect="low",
    )
    assert "CAREFUL SPEECH" in text
    assert "profile:grief" in text
    assert "brutal_truth_mode=off" in text
    assert "avoid_wording" in text


def test_stall_profile_when_horizon_longer():
    profiles = profiles_for(
        moment_kinds=[],
        protocols=["P1_depression"],
        affect="low",
        stall_horizon="much_longer",
    )
    keys = [p.key for p in profiles]
    assert "stall" in keys or "depression" in keys


def test_realtime_injects_careful_speech(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h" / "memories").mkdir(parents=True)
    from lotus.realtime.core import RealtimeCore

    core = RealtimeCore()
    ctx = core.before_turn("I feel so numb and empty — please don't say just think positive")
    assert "CAREFUL SPEECH" in ctx
    assert "profile:" in ctx
