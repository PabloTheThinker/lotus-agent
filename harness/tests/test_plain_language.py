from lotus.plain_language import (
    glossary_hits,
    looks_medical,
    plain_language_directive,
    try_openmed,
)
from lotus.realtime.core import RealtimeCore


def test_looks_medical_detects_clinical_note():
    text = "Patient with hypertension and dyspnea; follow-up on lab results."
    assert looks_medical(text)


def test_glossary_hits():
    hits = dict(glossary_hits("History of hypertension and PRN meds"))
    assert hits["hypertension"] == "high blood pressure"
    assert "prn" in hits


def test_openmed_absent_returns_none(monkeypatch):
    monkeypatch.setenv("LOTUS_OPENMED_DISABLE", "1")
    assert try_openmed("hypertension and dyspnea") is None


def test_directive_mentions_fallback_without_openmed(monkeypatch):
    monkeypatch.setenv("LOTUS_OPENMED_DISABLE", "1")
    text = plain_language_directive("idiopathic etiology and NPO")
    assert "MEDICAL → NATURAL LANGUAGE" in text
    assert "glossary" in text.lower() or "OpenMed not installed" in text


def test_realtime_injects_plain_language_bridge(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "h"))
    monkeypatch.setenv("LOTUS_OPENMED_DISABLE", "1")
    (tmp_path / "h").mkdir()
    core = RealtimeCore()
    ctx = core.before_turn(
        "The discharge note says idiopathic etiology and NPO after midnight — what does that mean?"
    )
    assert "MEDICAL → NATURAL LANGUAGE" in ctx
    assert "idiopathic" in ctx.lower() or "npo" in ctx.lower()
