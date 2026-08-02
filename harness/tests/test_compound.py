from lotus.compound import reset_compound


def test_mission_captured_from_user_goal(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h" / "memories").mkdir(parents=True)
    eng = reset_compound()
    eng.after_turn(
        "I want to rebuild my mornings so I can feel human again.",
        "We can take one secure step when you're ready.",
        protocols=["P1_depression"],
        affect="low",
    )
    mission = eng.state.active()
    assert mission is not None
    assert "rebuild" in mission.statement.lower() or "mornings" in mission.statement.lower()
    center = mission.center_checkpoint()
    assert center is not None
    assert center.is_center
    assert mission.meter.center_met is False
    assert mission.meter.guidance_unlocked is False
    ctx = eng.before_turn("What's one small checkpoint?", affect="low")
    assert "Body/Contact" in ctx or "crisis-line homework" in ctx
    # First non-center seed should be body steadiness, not crisis homework
    body = next(c for c in mission.checkpoints if c.ladder_rung == "body")
    assert "steadiness" in body.title.lower() or "body" in body.title.lower()


def test_center_met_unlocks_guidance(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h" / "memories").mkdir(parents=True)
    eng = reset_compound()
    eng.after_turn("I want to get through grief without drowning.", "", protocols=["P3_grief"])
    eng.after_turn(
        "I'm safe tonight — I reached out to a friend and I'm not alone.",
        "I'm glad you reached.",
        affect="calm",
    )
    mission = eng.state.active()
    assert mission is not None
    assert mission.meter.center_met is True
    assert mission.meter.guidance_unlocked is True
    ctx = eng.before_turn("what next?", affect="calm")
    assert "center met" in ctx.lower() or "GUIDANCE MODE: center met" in ctx


def test_stall_extends_journey_horizon(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h" / "memories").mkdir(parents=True)
    eng = reset_compound()
    eng.after_turn("My goal is to leave the house once a week.", "")
    eng.after_turn("I'm still stuck and can't make any progress — this is taking forever.", "")
    eng.after_turn("I failed again and I'm back to square one.", "")
    eng.after_turn("Still going nowhere.", "")
    mission = eng.state.active()
    assert mission is not None
    assert mission.meter.stall_count >= 2
    assert mission.meter.estimated_horizon in {"longer", "much_longer"}
    kinds = {r.kind for r in eng.state.records}
    assert "stall" in kinds
    assert "journey_extended" in kinds or mission.meter.estimated_horizon == "longer"


def test_progress_moves_meter(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h" / "memories").mkdir(parents=True)
    eng = reset_compound()
    eng.after_turn("I want to rebuild sleep.", "")
    eng.after_turn("I'm safe and I asked for help.", "", affect="calm")
    before = eng.state.active().meter.compound_score
    eng.after_turn("I did take a step — I managed to sleep before midnight.", "", affect="rising")
    after = eng.state.active().meter
    assert after.progress_count >= 1
    assert after.compound_score >= before
    assert after.checkpoints_met >= 1


def test_crisis_pauses_mission_guidance(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h" / "memories").mkdir(parents=True)
    eng = reset_compound()
    eng.after_turn("I want to heal.", "")
    eng.after_turn("everything is falling apart", "", crisis=True, affect="crisis")
    mission = eng.state.active()
    assert mission is not None
    assert mission.status == "paused"
    ctx = eng.before_turn("hello", crisis=True, affect="crisis")
    assert "CRISIS" in ctx
    assert "pause" in ctx.lower()


def test_before_turn_without_mission(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h" / "memories").mkdir(parents=True)
    eng = reset_compound()
    ctx = eng.before_turn("I feel numb")
    assert "No active user mission" in ctx
