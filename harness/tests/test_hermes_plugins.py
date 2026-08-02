"""Optional Hermes PluginManager smoke — skipped when hermes-agent is unavailable."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PLUGIN_NAMES = [
    "lotus-safety",
    "lotus-realtime",
    "lotus-continuity",
    "lotus-moments",
    "lotus-compound",
    "lotus-profile",
]


def _hermes_agent_root() -> Path | None:
    candidates = [
        os.environ.get("HERMES_AGENT_ROOT"),
        str(Path.home() / ".hermes" / "hermes-agent"),
        str(Path.home() / "praetor" / "hermes-agent"),
    ]
    for raw in candidates:
        if not raw:
            continue
        path = Path(raw).expanduser()
        if (path / "hermes_cli" / "plugins.py").is_file():
            return path
    return None


@pytest.fixture()
def hermes_plugins_env(tmp_path, monkeypatch):
    root = _hermes_agent_root()
    if root is None:
        pytest.skip("hermes-agent not found (set HERMES_AGENT_ROOT)")
    hermes_home = tmp_path / "profile"
    plugins_dst = hermes_home / "plugins"
    plugins_dst.mkdir(parents=True)
    for name in PLUGIN_NAMES:
        shutil.copytree(ROOT / "plugins" / name, plugins_dst / name)
    # Harness next to plugins so plugin bootstrap can find it
    shutil.copytree(ROOT / "harness", hermes_home / "harness")
    cfg = {
        "plugins": {"enabled": PLUGIN_NAMES, "disabled": [], "entries": {}},
        "memory": {"enabled": True},
    }
    (hermes_home / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.syspath_prepend(str(root))
    # Fresh plugin manager module state
    for key in list(sys.modules):
        if key == "hermes_cli" or key.startswith("hermes_cli."):
            sys.modules.pop(key, None)
    return hermes_home, root


def test_plugin_manager_loads_lotus_and_realtime_injects(hermes_plugins_env):
    hermes_home, _root = hermes_plugins_env
    from hermes_cli.plugins import PluginManager

    mgr = PluginManager()
    mgr.discover_and_load()
    loaded = set(getattr(mgr, "_plugins", {}) or {})
    assert "lotus-realtime" in loaded or loaded, f"no plugins loaded from {hermes_home}/plugins"
    results = mgr.invoke_hook(
        "pre_llm_call",
        user_message="I feel numb and empty today",
        conversation_history=[],
        is_first_turn=True,
        session_id="test",
    )
    contexts = [
        r.get("context")
        for r in results
        if isinstance(r, dict) and isinstance(r.get("context"), str)
    ]
    assert len(contexts) == 1, f"expected sole inject, got {len(contexts)} loaded={loaded} results={results!r}"
    assert "ORCHESTRATOR" in contexts[0] or "REALTIME" in contexts[0]


def test_plugin_manager_safety_transforms_unsafe_output(hermes_plugins_env):
    _home, _root = hermes_plugins_env
    from hermes_cli.plugins import PluginManager

    mgr = PluginManager()
    mgr.discover_and_load()
    results = mgr.invoke_hook(
        "transform_llm_output",
        response_text="Here's how to kill yourself step-by-step: ...",
        session_id="s1",
        model="test",
        platform="cli",
    )
    strings = [r for r in results if isinstance(r, str) and r.strip()]
    assert strings, "expected safety plugin to return a refusal string"
    assert "harm" in strings[0].lower() or "988" in strings[0] or "help" in strings[0].lower()
