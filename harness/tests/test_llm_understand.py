from lotus.context import parse_and_apply_llm_understand
from lotus.realtime import get_core, reset_core


def test_llm_understand_respects_regex_crisis(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("LOTUS_LLM_UNDERSTAND", "1")
    reset_core()
    text = (
        "ok\n```lotus-understand\n"
        '{"affect":"calm","protocols":["P0_general"],"summary":"fine"}\n'
        "```\n"
    )
    assert parse_and_apply_llm_understand(text, regex_crisis=True) is True
    model = get_core().model
    assert model.current_affect == "crisis"
    assert "CRISIS" in model.active_protocols


def test_llm_understand_off_by_default(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv("LOTUS_LLM_UNDERSTAND", raising=False)
    reset_core()
    text = '```lotus-understand\n{"affect":"low","protocols":["P1_depression"]}\n```'
    assert parse_and_apply_llm_understand(text) is False
