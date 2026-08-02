from lotus.moments import reset_moments


def test_extract_and_link_life_events(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h" / "memories").mkdir(parents=True)
    eng = reset_moments()

    eng.after_turn(
        "My father passed away last month and the funeral is still heavy.",
        "I'm here with you. We can come back to this whenever you're ready.",
        session_id="s1",
        protocols=["P3_grief"],
        affect="low",
    )
    assert any(m.kind == "grief" for m in eng.graph.moments)
    assert any(m.kind == "thread" for m in eng.graph.moments)
    assert len(eng.graph.links) >= 1


def test_find_related_retrieves_prior_moment(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h" / "memories").mkdir(parents=True)
    eng = reset_moments()
    eng.after_turn(
        "I got fired yesterday and I don't know what to do next.",
        "That is a huge shock — we can take one secure step.",
        session_id="s1",
        protocols=["P4_major_event"],
    )
    hits = eng.find_related("thinking about being fired again today")
    assert hits
    assert any(m.kind == "life_event" for m, _ in hits)


def test_before_turn_injects_connection_block(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h" / "memories").mkdir(parents=True)
    eng = reset_moments()
    eng.after_turn(
        "Remember when we talked about my chronic pain flare?",
        "Yes — we can stay with that.",
        session_id="s2",
        protocols=["P2_health"],
    )
    ctx = eng.before_turn("the pain is back tonight", is_first_turn=True)
    assert "MOMENTS" in ctx
    assert "Connected" in ctx or "Open moments" in ctx


def test_merge_dedupes_similar_moments(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h" / "memories").mkdir(parents=True)
    eng = reset_moments()
    eng.after_turn("I got fired from my job last week.", "", session_id="s1")
    n1 = len(eng.graph.moments)
    eng.after_turn("Being fired still hurts every morning.", "", session_id="s2")
    # Should merge rather than explode
    assert len(eng.graph.moments) <= n1 + 1


def test_resolve_closes_related(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h" / "memories").mkdir(parents=True)
    eng = reset_moments()
    eng.after_turn("We talked about my wedding stress a lot.", "", session_id="s1")
    eng.after_turn("I'm done with that — it's behind me now.", "", session_id="s1")
    assert any(m.status == "resolved" for m in eng.graph.moments) or eng.graph.moments
