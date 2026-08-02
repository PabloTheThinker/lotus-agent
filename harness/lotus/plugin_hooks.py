"""Shared helpers for thin Hermes plugins — stop copy-pasting across plugins."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def env_disabled(flag: str) -> bool:
    return os.environ.get(flag, "").lower() in {"1", "true", "yes", "on"}


def bootstrap(plugin_file: str | Path) -> None:
    from lotus.plugin_bootstrap import bootstrap_from_plugin_file

    bootstrap_from_plugin_file(Path(plugin_file))


def as_text(user_message: Any) -> str:
    if isinstance(user_message, str):
        return user_message
    if isinstance(user_message, list):
        parts: List[str] = []
        for block in user_message:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(user_message or "")


def living_snapshot() -> Tuple[str, List[str]]:
    """Return (affect, protocols) from living model — best effort."""
    try:
        from lotus.realtime.model import LivingUserModel

        m = LivingUserModel.load()
        return m.current_affect or "", list(m.active_protocols or [])
    except Exception:
        return "", []


def living_affect_protocol() -> Tuple[str, str]:
    affect, protocols = living_snapshot()
    return affect, (protocols[0] if protocols else "")


def is_crisis(text: str, affect: str = "") -> bool:
    if affect == "crisis":
        return True
    try:
        from lotus.guardrails import assess_user_text

        return assess_user_text(text).inject_crisis_override
    except Exception:
        return False


def context_result(ctx: Optional[str]) -> Optional[Dict[str, str]]:
    if not ctx or not str(ctx).strip():
        return None
    return {"context": str(ctx)}
