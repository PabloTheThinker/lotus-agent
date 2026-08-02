from lotus.prefs import (
    UserPrefs,
    detect_lang,
    maybe_autodetect_lang,
    reset_prefs,
    resolve_crisis_regions,
    update_prefs,
)


def test_resolve_regions_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("LOTUS_CRISIS_REGIONS", "GB,AU")
    reset_prefs()
    assert resolve_crisis_regions()[0] == "GB"
    assert "INTL" in resolve_crisis_regions()


def test_prefs_persist_lang_and_regions(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv("LOTUS_CRISIS_REGIONS", raising=False)
    reset_prefs()
    prefs = update_prefs(preferred_lang="es", crisis_regions=["CA"])
    assert prefs.preferred_lang == "es"
    assert prefs.lang_locked is True
    assert prefs.crisis_regions[0] == "CA"
    assert "INTL" in prefs.crisis_regions
    again = UserPrefs.load()
    assert again.preferred_lang == "es"


def test_autodetect_lang_soft_update(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv("LOTUS_PREFERRED_LANG", raising=False)
    reset_prefs()
    assert detect_lang("Me siento deprimido y quiero ayuda") == "es"
    applied = maybe_autodetect_lang("Me siento deprimido y quiero ayuda")
    assert applied == "es"
    assert UserPrefs.load().preferred_lang == "es"
    assert UserPrefs.load().lang_locked is False
    # Unlocked: English turn soft-resets so Spanish does not stick forever
    assert maybe_autodetect_lang("hey — I'm back and I feel numb today") == "en"
    assert UserPrefs.load().preferred_lang == "en"
    # Locked prefs are not overwritten
    update_prefs(preferred_lang="en", lang_locked=True)
    assert maybe_autodetect_lang("Me siento triste") is None
    assert UserPrefs.load().preferred_lang == "en"
