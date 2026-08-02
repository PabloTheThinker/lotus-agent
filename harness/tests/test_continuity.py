from lotus.continuity.engine import ContinuityEngine


def test_continuity_resume_and_threads(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h").mkdir()

    eng = ContinuityEngine()
    eng.on_session_start(session_id="s1", platform="cli")
    ctx = eng.before_turn(
        "I'm not ready to go deeper yet, maybe later",
        is_first_turn=True,
        living_affect="low",
        living_protocol="P1_depression",
    )
    assert "CONTINUITY" in ctx
    eng.after_turn(
        "I'm not ready to go deeper yet, maybe later",
        "That's okay — we can come back whenever you're ready.",
        living_affect="low",
        living_protocol="P1_depression",
    )
    assert eng.state.open_threads
    eng.on_session_end()

    eng2 = ContinuityEngine()
    ctx2 = eng2.before_turn("hey", is_first_turn=True)
    assert "resume" in ctx2.lower() or eng2.state.resume_summary


def test_memory_promotion_queued(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h").mkdir()
    eng = ContinuityEngine()
    eng.after_turn("I prefer short replies please", "Got it — I'll keep it short.")
    assert any("prefer" in p.get("content", "").lower() for p in eng.state.memory_promotions)
    sync = tmp_path / "h" / "memories" / "lotus-core" / "MEMORY_SYNC.md"
    assert sync.exists()
