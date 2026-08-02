from lotus.honcho import honcho_context_block, honcho_status


def test_honcho_inactive_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    (tmp_path / "config.yaml").write_text("memory:\n  enabled: true\n", encoding="utf-8")
    ok, detail = honcho_status(tmp_path)
    assert ok is False
    assert "not configured" in detail or "optional" in detail
    assert honcho_context_block() is None


def test_honcho_active_when_provider_and_key(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("HONCHO_API_KEY", "test-key")
    (tmp_path / "config.yaml").write_text(
        "memory:\n  enabled: true\n  provider: honcho\n",
        encoding="utf-8",
    )
    ok, detail = honcho_status(tmp_path)
    assert ok is True
    assert "active" in detail
    # get_or_read uses hermes_home() from env
    block = honcho_context_block()
    assert block and "HONCHO" in block
