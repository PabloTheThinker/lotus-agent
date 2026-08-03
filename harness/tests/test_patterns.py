"""Pattern recognition + talk plan + meta scrub + way-out / shock."""

from lotus.speech import build_speech_care_directive
from lotus.speech.flow import scrub_verbal_tics
from lotus.speech.patterns import (
    TalkPatternMemory,
    build_talk_plan,
    learn_from_turn,
    recognize_hits,
    talk_plan_block,
)


def test_reassurance_need_from_broken_question():
    plan = build_talk_plan(
        "does that make sense or am i just broken?",
        protocols=["P1_depression"],
        memory=TalkPatternMemory(),
    )
    assert plan.need in {"reassure", "answer", "way_out"}
    assert plan.max_sentences <= 6


def test_way_out_beats_soft_company():
    plan = build_talk_plan(
        "i don't want a five step thing but i don't know how people get out of this dark. "
        "i need something real.",
        memory=TalkPatternMemory(),
    )
    assert plan.need in {"way_out", "hard_path"}
    assert plan.way_out_line
    assert "talk" in plan.move.lower()
    assert "timer" in plan.move.lower() or "homework" in plan.move.lower() or "FORBIDDEN" in plan.move


def test_friend_shock_mom_hospital():
    plan = build_talk_plan(
        "omg my mom's in the hospital. i just found out",
        memory=TalkPatternMemory(),
    )
    assert plan.need == "friend_shock"
    assert plan.reply_shape == "sms_burst"
    assert "what happened" in plan.move.lower()


def test_soft_loop_escalates_to_hard_path():
    mem = TalkPatternMemory(soft_loop_count=3)
    plan = build_talk_plan(
        "everything still feels flat and empty in the dark",
        protocols=["P1_depression"],
        memory=mem,
    )
    assert plan.need == "hard_path"
    assert plan.intensity == "hard"


def test_gateway_in_speech_directive():
    text = build_speech_care_directive(
        user_text="everything feels flat and empty",
        protocols=["P1_depression"],
        affect="low",
    )
    assert "CHARACTER" in text or "GATEWAY" in text
    assert "Real talk" in text or "real talk" in text  # banned list mentions it
    assert "RESPONSE SHAPE" not in text
    assert "--- profile:" not in text  # no profile essay dump


def test_scrub_meta_and_heart_cliche():
    raw = (
        "Hurting this hard makes waiting feel useless. "
        "Hearts get wrecked and still come back. "
        "I'm not handing you a to-do list."
    )
    cleaned = scrub_verbal_tics(raw)
    assert "to-do list" not in cleaned.lower()
    assert "hearts get wrecked" not in cleaned.lower()


def test_learn_way_out_clears_soft_company(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    mem = learn_from_turn(
        "i don't know how people get out of this. what's even the point",
        "The crawl out is uneven — people usually leave by naming the weight out loud first.",
    )
    assert mem.soft_company is False
    assert any("way out" in n for n in mem.notes)


def test_sync_pattern_memory_into_living_model(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from lotus.realtime.model import LivingUserModel
    from lotus.speech.patterns import sync_pattern_memory_to_model

    mem = TalkPatternMemory(
        turn_count=4,
        prefers_short=True,
        hates_worksheets=True,
        hates_meta=True,
        soft_loop_count=3,
        need_counts={"way_out": 2, "reassure": 1},
        notes=["asked for a way out — give a real path"],
    )
    model = LivingUserModel()
    sync_pattern_memory_to_model(model, mem)
    assert model.voice_style.get("reply_length") == "short"
    assert model.voice_style.get("hates_worksheets") is True
    assert "no_worksheets" in model.prompt_block() or "talk_patterns" in model.prompt_block()
    assert any("short SMS" in x for x in model.preferred_language)


def test_gateway_pace_and_refusal():
    from lotus.speech.gateway import gateway_block

    slow = gateway_block("you're talking too slow. just say it.")
    assert "PACE=faster" in slow
    refuse = gateway_block("nah. i'm not doing that timer thing.")
    assert "REFUSAL" in refuse


def test_recognize_numb_dark():
    hits = {h.name for h in recognize_hits("watching my life from the hallway, flat")}
    assert "numb_dark" in hits


def test_talk_plan_block_has_friend_examples():
    plan = build_talk_plan("omg my mom's in the hospital", memory=TalkPatternMemory())
    block = talk_plan_block(plan)
    assert "GOOD shock:" in block or "what happened" in block.lower()
