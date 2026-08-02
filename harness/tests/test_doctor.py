from lotus.doctor import run_doctor


def test_doctor_runs(tmp_path, monkeypatch):
    home = tmp_path / "lotus"
    home.mkdir()
    (home / "SOUL.md").write_text("# soul\n", encoding="utf-8")
    (home / "plugins" / "lotus-safety").mkdir(parents=True)
    (home / "plugins" / "lotus-realtime").mkdir(parents=True)
    (home / "plugins" / "lotus-continuity").mkdir(parents=True)
    (home / "plugins" / "lotus-moments").mkdir(parents=True)
    (home / "plugins" / "lotus-compound").mkdir(parents=True)
    (home / "plugins" / "lotus-profile").mkdir(parents=True)
    (home / "skins").mkdir()
    (home / "skins" / "lotus.yaml").write_text("name: lotus\n", encoding="utf-8")
    (home / "dashboard-themes").mkdir()
    (home / "dashboard-themes" / "lotus.yaml").write_text("name: lotus\n", encoding="utf-8")
    (home / ".env").write_text(
        "OPENROUTER_API_KEY=test\nAPI_SERVER_ENABLED=true\nAPI_SERVER_KEY=secret\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    report = run_doctor(str(home))
    names = {c.name: c for c in report.checks}
    assert names["profile_home"].ok
    assert names["env_file"].ok
    assert names["model_provider"].ok
    assert names["harness_import"].ok
    assert names["plugins"].ok
