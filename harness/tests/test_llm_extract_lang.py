from lotus.context.orchestrator import parse_and_apply_llm_extract
from lotus.prefs import UserPrefs, reset_prefs


def test_extract_preferred_lang_locks_prefs(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    monkeypatch.setenv("LOTUS_LLM_EXTRACT", "1")
    monkeypatch.delenv("LOTUS_PREFERRED_LANG", raising=False)
    (tmp_path / "h").mkdir()
    reset_prefs()

    text = (
        "Sure.\n"
        "```lotus-extract\n"
        '{"preferred_name":"Sam","preferred_lang":"es","mission":"","supports":[],'
        '"avoid_words":[],"notes":""}\n'
        "```\n"
    )
    assert parse_and_apply_llm_extract(text) is True
    prefs = UserPrefs.load()
    assert prefs.preferred_lang == "es"
    assert prefs.lang_locked is True
