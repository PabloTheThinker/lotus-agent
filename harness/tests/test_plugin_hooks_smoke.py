"""Hermes plugin register() smoke — no live Hermes required."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGINS = ROOT / "plugins"


class FakeCtx:
    def __init__(self) -> None:
        self.hooks: list[tuple[str, object]] = []

    def register_hook(self, name: str, fn: object) -> None:
        self.hooks.append((name, fn))


def _load_register(name: str):
    path = PLUGINS / name / "__init__.py"
    spec = importlib.util.spec_from_file_location(f"plugin_{name}", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod.register


def test_all_lotus_plugins_register_expected_hooks():
    expected = {
        "lotus-safety": {"transform_llm_output"},
        "lotus-realtime": {"pre_llm_call", "post_llm_call", "on_session_start"},
        "lotus-continuity": {"on_session_start", "post_llm_call", "on_session_end"},
        "lotus-moments": {"on_session_start", "post_llm_call", "on_session_end"},
        "lotus-compound": {"on_session_start", "post_llm_call"},
        "lotus-profile": {"on_session_start"},
    }
    for name, hooks in expected.items():
        register = _load_register(name)
        ctx = FakeCtx()
        register(ctx)
        got = {h for h, _ in ctx.hooks}
        assert got == hooks, f"{name}: {got} != {hooks}"
        # Only realtime may inject context from pre_llm_call
        if name != "lotus-realtime":
            assert "pre_llm_call" not in got
