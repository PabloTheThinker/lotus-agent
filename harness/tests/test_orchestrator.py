"""Context orchestrator — merge, budget, LLM extract, multi-plugin turn path."""

from __future__ import annotations

import pytest

from lotus.compound import get_compound, reset_compound
from lotus.context.orchestrator import (
    ContextBlock,
    build_turn_context,
    merge_blocks,
    merge_blocks_detailed,
    parse_and_apply_llm_extract,
)
from lotus.continuity import get_continuity, reset_continuity
from lotus.moments import get_moments, reset_moments
from lotus.profile import get_profile, reset_profile
from lotus.realtime.core import RealtimeCore, reset_core


@pytest.fixture()
def hermes_tmp(tmp_path, monkeypatch):
    home = tmp_path / "hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    for reset in (reset_core, reset_continuity, reset_moments, reset_compound, reset_profile):
        try:
            reset()
        except Exception:
            pass
    return home


def test_merge_blocks_respects_budget():
    blocks = [
        ContextBlock("a", 0, "A" * 100, sticky=True),
        ContextBlock("b", 10, "B" * 100, sticky=False),
        ContextBlock("c", 20, "C" * 100, sticky=False),
    ]
    out = merge_blocks(blocks, budget=180)
    assert "A" * 20 in out
    assert "C" * 20 not in out or len(out) <= 180


def test_merge_keeps_sticky_when_over_budget():
    blocks = [
        ContextBlock("safe", 0, "SAFETY " * 40, sticky=True),
        ContextBlock("low", 50, "LOWPRI " * 40, sticky=False),
    ]
    out = merge_blocks(blocks, budget=80)
    assert "SAFETY" in out
    assert "LOWPRI" not in out or "…[truncated]" in out


def test_merge_detailed_reports_drops():
    blocks = [
        ContextBlock("safe", 0, "SAFETY " * 20, sticky=True),
        ContextBlock("low", 50, "LOWPRI " * 40, sticky=False),
    ]
    result = merge_blocks_detailed(blocks, budget=80)
    assert "safe" in result.kept
    assert "low" in result.dropped


def test_build_turn_context_single_header(hermes_tmp, monkeypatch):
    monkeypatch.delenv("LOTUS_LLM_EXTRACT", raising=False)
    ctx = build_turn_context("I feel numb and empty today")
    assert "CONTEXT ORCHESTRATOR" in ctx
    assert "REALTIME CORE" in ctx or "living user model" in ctx
    assert ctx.count("[L.O.T.U.S. CONTEXT ORCHESTRATOR]") == 1


def test_crisis_block_sticky_in_orchestrator(hermes_tmp):
    ctx = build_turn_context("I want to kill myself")
    assert "CRISIS" in ctx
    assert "SAFETY" in ctx


def test_multi_plugin_turn_simulation(hermes_tmp):
    """Simulate Hermes turn: one inject + post hooks from each subsystem."""
    user = "I want to rebuild my life after the breakup"
    core = RealtimeCore()
    inject = core.before_turn(user, is_first_turn=True)
    assert "ORCHESTRATOR" in inject or "REALTIME" in inject

    assistant = "I'm with you. One secure step: drink water and sit upright for a minute."
    core.after_turn(user, assistant)
    get_continuity().after_turn(user, assistant, living_affect="mixed", living_protocol="P4_major_event")
    get_moments().after_turn(user, assistant, protocols=["P4_major_event"], affect="mixed")
    get_compound().after_turn(user, assistant, protocols=["P4_major_event"], affect="mixed")
    get_profile().after_turn(
        user,
        assistant,
        living_model=core.model,
        protocols=["P4_major_event"],
        affect="mixed",
    )

    # Second turn should still be a single orchestrated inject
    inject2 = core.before_turn("that helped a little", is_first_turn=False)
    assert "ORCHESTRATOR" in inject2
    assert inject2.count("[L.O.T.U.S. CONTEXT ORCHESTRATOR]") == 1


def test_llm_extract_gated_off(hermes_tmp, monkeypatch):
    monkeypatch.delenv("LOTUS_LLM_EXTRACT", raising=False)
    text = 'ok\n```lotus-extract\n{"preferred_name":"Sam"}\n```\n'
    assert parse_and_apply_llm_extract(text) is False


def test_llm_extract_applies_when_on(hermes_tmp, monkeypatch):
    monkeypatch.setenv("LOTUS_LLM_EXTRACT", "1")
    text = 'ok\n```lotus-extract\n{"preferred_name":"Sam","supports":["sister"]}\n```\n'
    assert parse_and_apply_llm_extract(text) is True
    prof = get_profile().profile
    assert prof.preferred_name == "Sam"
    assert any("sister" in s.lower() for s in prof.supports)
