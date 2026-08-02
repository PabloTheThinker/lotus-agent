from lotus.moments import reset_moments
from lotus.protocols import Protocol, classify_protocol
from lotus.realtime.understanding import UnderstandingSubroutine


def test_depression_spanish_protocol():
    assert classify_protocol("me siento deprimido y vacío") == Protocol.DEPRESSION


def test_grief_french_protocol():
    assert classify_protocol("je suis en deuil après le décès") == Protocol.GRIEF


def test_affect_portuguese_low(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    snap = UnderstandingSubroutine().read("estou sem esperança e vazio")
    assert snap.affect.valence in {"low", "crisis"}


def test_moments_detect_spanish_grief(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    eng = reset_moments()
    eng.after_turn(
        "mi padre falleció la semana pasada y estoy en duelo",
        "Estoy contigo.",
        protocols=["P3_grief"],
        affect="low",
    )
    kinds = {m.kind for m in eng.graph.moments}
    assert "grief" in kinds
