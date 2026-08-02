from pathlib import Path

from lotus.doctor import _check_research_pulse_artifact
from lotus.realtime.core import RealtimeCore


def test_pulse_artifact_warns_when_empty(tmp_path):
    home = tmp_path / "h"
    home.mkdir()
    ok, detail = _check_research_pulse_artifact(home)
    assert ok is False
    assert "research-seed" in detail or "cron" in detail


def test_pulse_artifact_ok_after_seed(tmp_path, monkeypatch):
    home = tmp_path / "h"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    core = RealtimeCore()
    core.research.seed_offline_approaches(core.model)
    core.model.save()
    ok, detail = _check_research_pulse_artifact(home)
    assert ok is True
    assert "approaches" in detail.lower() or "help_approaches" in detail
    assert Path(home / "memories" / "lotus-core" / "research_log.jsonl").is_file()
