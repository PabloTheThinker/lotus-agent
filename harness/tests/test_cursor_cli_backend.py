from lotus.backends.cursor_cli import (
    CursorCliBackend,
    _compose_prompt,
    resolve_backend,
)


def test_resolve_backend_aliases():
    assert resolve_backend("hermes") == "hermes"
    assert resolve_backend("cursor") == "cursor"
    assert resolve_backend("grok") == "cursor"
    assert resolve_backend("cursor-cli") == "cursor"


def test_compose_prompt_includes_system_and_user():
    p = _compose_prompt(
        "I feel numb",
        system_prompt="[L.O.T.U.S. CONTEXT]\nbe gentle",
        history=[{"role": "user", "content": "hi"}, {"role": "assistant", "content": "here"}],
    )
    assert "I feel numb" in p
    assert "be gentle" in p
    assert "USER MESSAGE" in p


def test_cursor_backend_mocked_subprocess(monkeypatch, tmp_path):
    calls = {}

    class FakeProc:
        returncode = 0
        stdout = "I'm here with you.\n"
        stderr = ""

    def fake_run(cmd, **kwargs):
        calls["cmd"] = cmd
        calls["cwd"] = kwargs.get("cwd")
        return FakeProc()

    monkeypatch.setattr("lotus.backends.cursor_cli.subprocess.run", fake_run)
    monkeypatch.setattr(
        "lotus.backends.cursor_cli.shutil.which",
        lambda x: "/usr/bin/agent",
    )
    backend = CursorCliBackend(model="cursor-grok-4.5-high-fast", cwd=str(tmp_path))
    out = backend.complete("hello", system_prompt="sys")
    assert out == "I'm here with you."
    assert calls["cmd"][0] == "/usr/bin/agent"
    assert "--model" in calls["cmd"]
    assert "cursor-grok-4.5-high-fast" in calls["cmd"]
    assert "--trust" in calls["cmd"]
