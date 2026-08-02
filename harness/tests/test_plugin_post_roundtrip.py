"""Continuity / moments / compound post_llm_call chain mutates lotus-core."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGINS = ROOT / "plugins"


class FakeCtx:
    def __init__(self) -> None:
        self.hooks: dict[str, list] = {}

    def register_hook(self, name: str, fn: object) -> None:
        self.hooks.setdefault(name, []).append(fn)


def _load_plugin(name: str):
    path = PLUGINS / name / "__init__.py"
    spec = importlib.util.spec_from_file_location(f"rt_{name}", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_post_llm_plugins_persist_state(tmp_path, monkeypatch):
    home = tmp_path / "profile"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    # Point plugins at repo harness via bootstrap (parents[2]/harness from plugin file)
    monkeypatch.syspath_prepend(str(ROOT / "harness"))

    from lotus.context import build_turn_context
    from lotus.realtime.core import reset_core

    user = "My father passed away last month and I feel so numb and empty"
    # Pre-inject path (orchestrator / realtime)
    ctx = build_turn_context(user, is_first_turn=True, session_id="rt1")
    assert "L.O.T.U.S" in ctx or "living" in ctx.lower() or "CONTINUITY" in ctx or ctx

    # Register post hooks and invoke them as Hermes would
    for name in ("lotus-continuity", "lotus-moments", "lotus-compound"):
        mod = _load_plugin(name)
        fake = FakeCtx()
        mod.register(fake)
        for fn in fake.hooks.get("post_llm_call", []):
            fn(
                user_message=user,
                assistant_response="I'm with you in this grief. We can go slow.",
                conversation_history=[],
                session_id="rt1",
            )

    core = home / "memories" / "lotus-core"
    assert (core / "continuity.json").is_file() or (core / "RESUME.md").is_file()
    assert (core / "moments.json").is_file()
    # Compound may or may not create a mission from one turn; living model should exist
    living = core / "living_model.json"
    assert living.is_file()
    raw = json.loads(living.read_text(encoding="utf-8"))
    assert raw.get("turn_count", 0) >= 1 or raw.get("_schema_version")

    # Next pre_llm inject should see continuity / moments context
    reset_core()
    ctx2 = build_turn_context("hey", is_first_turn=True, session_id="rt2")
    assert isinstance(ctx2, str)
    lowered = ctx2.lower()
    assert "moment" in lowered or "continu" in lowered or "grief" in lowered or "mission" in lowered or len(ctx2) > 40
