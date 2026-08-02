
import pytest

from lotus.realtime.core import RealtimeCore
from lotus.realtime.model import LivingUserModel


@pytest.fixture()
def hermes_tmp(tmp_path, monkeypatch):
    home = tmp_path / "hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    return home


def test_before_turn_injects_living_model(hermes_tmp):
    core = RealtimeCore()
    ctx = core.before_turn("I feel so numb and empty today")
    assert "REALTIME CORE" in ctx or "living user model" in ctx
    assert "P1_depression" in ctx or "depression" in ctx.lower()
    assert (hermes_tmp / "memories" / "lotus-core" / "living_model.json").exists()


def test_learning_captures_help_feedback(hermes_tmp):
    core = RealtimeCore()
    core.before_turn("everything hurts")
    core.after_turn(
        "that really helped when you slowed down with me",
        "I'm glad. One small step: drink a glass of water.",
    )
    model = LivingUserModel.load()
    assert model.turn_count >= 1
    assert any("helped" in s.lower() or "slow" in s.lower() for s in model.successful_moves) or model.preferred_language or model.successful_moves


def test_research_queue_fills_from_gaps(hermes_tmp):
    core = RealtimeCore()
    core.before_turn("I've been depressed and don't know how to start")
    model = LivingUserModel.load()
    assert model.research_queue, model
    assert any(q.get("status") == "queued" for q in model.research_queue)


def test_insights_md_written(hermes_tmp):
    core = RealtimeCore()
    core.before_turn("My father passed away and I'm lost")
    core.after_turn("My father passed away and I'm lost", "I'm here with you in this grief.")
    insights = hermes_tmp / "memories" / "lotus-core" / "INSIGHTS.md"
    assert insights.exists()
    text = insights.read_text(encoding="utf-8")
    assert "Living Insights" in text


def test_understanding_snapshot_cached_across_pre_post(hermes_tmp, monkeypatch):
    """Pre-inject and post-turn share one understanding.read() call."""
    from lotus.realtime.core import get_core, reset_core

    core = reset_core()
    calls = {"n": 0}
    original = core.understanding.read

    def counted(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(core.understanding, "read", counted)
    user = "I feel numb and empty and don't know how to start"
    get_core().before_turn(user)
    assert calls["n"] == 1
    get_core().after_turn(user, "I'm with you. One small step.")
    assert calls["n"] == 1  # cache hit for same turn
    # Next turn clears cache and re-reads
    get_core().before_turn("that helped a little")
    assert calls["n"] == 2
