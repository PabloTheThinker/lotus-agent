from lotus.realtime.core import RealtimeCore


def test_offline_seed_fills_empty_approaches(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h").mkdir()
    core = RealtimeCore()
    assert core.model.help_approaches == []
    n = core.research.seed_offline_approaches(core.model)
    assert n >= 3
    assert len(core.model.help_approaches) >= 3
    # Idempotent while library non-empty
    assert core.research.seed_offline_approaches(core.model) == 0
    st = core.research.pulse_status(core.model)
    assert st["approaches"] >= 3
