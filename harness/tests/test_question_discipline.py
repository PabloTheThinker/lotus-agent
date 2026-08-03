from lotus.memory_sync import sync_for_production, write_memory_sync_md
from lotus.realtime.model import LivingUserModel
from lotus.speech.gateway import gateway_block
from lotus.speech.patterns import TalkPatternMemory, learn_from_turn
from lotus.speech.question_discipline import (
    question_discipline_flags,
    refuses_advice_or_lecture,
)


def test_refuses_lecture_detected():
    assert refuses_advice_or_lecture(
        "idk. just dont wanna hear how dumb it was. please dont lecture me"
    )


def test_gateway_zero_questions_on_no_lecture():
    text = gateway_block(
        "yeah i know. please dont lecture me about it rn",
        history=[
            {
                "role": "assistant",
                "content": "What were you reaching for when you sent it?",
            }
        ],
    )
    assert "QUESTION DISCIPLINE=zero" in text
    assert "ZERO" in text


def test_close_beat_flag():
    flags = question_discipline_flags("ok phone down. gonna try to sleep this off")
    assert any("CLOSE BEAT" in f for f in flags)


def test_learn_hates_lecture(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    mem = learn_from_turn(
        "please dont lecture me about it",
        "Fair. Not going to beat it into you.",
    )
    assert mem.hates_lecture is True


def test_memory_sync_writes_md(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    model = LivingUserModel()
    model.preferred_language = ["short SMS-length replies"]
    mem = TalkPatternMemory(
        turn_count=3,
        prefers_short=True,
        hates_worksheets=True,
        hates_lecture=True,
    )
    path = write_memory_sync_md(model, mem)
    assert path.is_file()
    body = path.read_text(encoding="utf-8")
    assert "SMS" in body or "short" in body.lower()
    assert "lecture" in body.lower() or "worksheet" in body.lower()
    directive = sync_for_production(model, mem)
    assert "HERMES MEMORY BRIDGE" in directive
