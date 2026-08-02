import json
import zipfile
from pathlib import Path

from lotus.privacy import export_core, summarize_core, wipe_core
from lotus.realtime.core import RealtimeCore


def test_export_and_wipe_roundtrip(tmp_path, monkeypatch):
    home = tmp_path / "h"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))

    core = RealtimeCore()
    core.before_turn("I feel numb and empty today")
    core.after_turn("I feel numb and empty today", "I'm here with you.")
    core.research.seed_offline_approaches(core.model)
    core.model.save()

    st = summarize_core()
    assert st["file_count"] >= 1

    zpath = export_core(tmp_path / "out.zip")
    assert zpath.is_file()
    with zipfile.ZipFile(zpath) as zf:
        names = set(zf.namelist())
        assert "MANIFEST.json" in names
        assert "living_model.json" in names
        manifest = json.loads(zf.read("MANIFEST.json"))
        assert "files" in manifest

    n, removed = wipe_core(keep_prefs=True, keep_approaches=False)
    assert n >= 1
    assert "living_model.json" in removed
    # After wipe, living model should be gone; prefs may remain if created
    assert not (home / "memories" / "lotus-core" / "living_model.json").exists()


def test_wipe_requires_explicit_cli_yes_documented(tmp_path, monkeypatch):
    """CLI refuses wipe without --yes (exercised via main)."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    (tmp_path / "h").mkdir()
    from lotus.cli import main

    rc = main(["privacy", "wipe"])
    assert rc == 2
