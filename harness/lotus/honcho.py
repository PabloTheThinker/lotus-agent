"""Honcho awareness for L.O.T.U.S. — Hermes memory provider, not a Lotus reimplementation.

Honcho is configured through Hermes (``hermes memory setup honcho``) for the
lotus profile. Lotus only detects presence and gently reminds the model to use
Honcho tools when available. Continuity stays file+hook based either way.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from lotus.realtime.paths import hermes_home


def _load_yaml_config(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        import yaml  # type: ignore

        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def honcho_status(home: Optional[Path] = None) -> Tuple[bool, str]:
    """Return (active, detail) for Honcho on this profile."""
    home = home or hermes_home()
    cfg = _load_yaml_config(home / "config.yaml")
    memory_raw = cfg.get("memory")
    memory: Dict[str, Any] = memory_raw if isinstance(memory_raw, dict) else {}
    provider = str(memory.get("provider") or "").strip().lower()

    config_candidates = [
        home / "honcho.json",
        Path.home() / ".hermes" / "honcho.json",
        Path.home() / ".honcho" / "config.json",
    ]
    honcho_cfg: Dict[str, Any] = {}
    cfg_path = None
    for path in config_candidates:
        if path.is_file():
            try:
                honcho_cfg = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(honcho_cfg, dict):
                    cfg_path = path
                    break
            except (json.JSONDecodeError, OSError):
                continue

    env_key = bool((os.environ.get("HONCHO_API_KEY") or "").strip())
    has_creds = bool(
        env_key
        or (isinstance(honcho_cfg, dict) and (honcho_cfg.get("apiKey") or honcho_cfg.get("baseUrl")))
    )

    if provider == "honcho" and has_creds:
        where = str(cfg_path) if cfg_path else "HONCHO_API_KEY"
        return True, f"active memory provider (config: {where})"
    if provider == "honcho" and not has_creds:
        return False, "memory.provider=honcho but no apiKey/baseUrl/HONCHO_API_KEY"
    if has_creds and provider != "honcho":
        return False, (
            "Honcho credentials present but not selected — "
            "run: hermes -p lotus memory setup honcho"
        )
    return False, "not configured — optional: hermes -p lotus memory setup honcho"


def honcho_context_block() -> Optional[str]:
    """Short orchestrator note when Honcho is the active Hermes memory provider."""
    active, detail = honcho_status()
    if not active:
        return None
    return (
        "[L.O.T.U.S. × HONCHO]\n"
        f"Honcho memory provider is active ({detail}).\n"
        "When durable user modeling helps, prefer Hermes Honcho tools "
        "(honcho_profile / honcho_search / honcho_context / honcho_reasoning / honcho_conclude) "
        "alongside lotus-core files. Do not invent Honcho facts. "
        "Crisis safety and lotus guardrails still override memory."
    )
