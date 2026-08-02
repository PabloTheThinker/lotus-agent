"""lotus-realtime — unified context inject + learning hooks."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _disabled() -> bool:
    return os.environ.get("LOTUS_REALTIME_DISABLE", "").lower() in {"1", "true", "yes", "on"}


def _boot():
    import sys

    here = Path(__file__).resolve()
    for candidate in (here.parents[2] / "harness", Path.home() / ".hermes" / "profiles" / "lotus" / "harness"):
        if (candidate / "lotus").is_dir():
            sp = str(candidate)
            if sp not in sys.path:
                sys.path.insert(0, sp)
            break
    from lotus.plugin_bootstrap import bootstrap_from_plugin_file

    bootstrap_from_plugin_file(here)


def _on_session_start(**kwargs: Any) -> None:
    if _disabled():
        return
    try:
        _boot()
        from lotus.realtime import get_core

        core = get_core()
        core.reload()
        logger.info(
            "lotus-realtime: session start — turns=%s affect=%s",
            core.model.turn_count,
            core.model.current_affect,
        )
    except Exception:
        logger.exception("lotus-realtime: on_session_start failed")


def _on_pre_llm_call(**kwargs: Any) -> Optional[Dict[str, str]]:
    if _disabled():
        return None
    try:
        _boot()
        from lotus.context import build_turn_context
        from lotus.plugin_hooks import as_text, context_result

        text = as_text(kwargs.get("user_message"))
        history = kwargs.get("conversation_history")
        if not isinstance(history, list):
            history = None
        ctx = build_turn_context(
            text,
            history=history,
            is_first_turn=bool(kwargs.get("is_first_turn")),
            session_id=str(kwargs.get("session_id") or ""),
        )
        return context_result(ctx)
    except Exception:
        logger.exception("lotus-realtime: pre_llm_call failed")
        return None


def _on_post_llm_call(**kwargs: Any) -> None:
    if _disabled():
        return
    try:
        _boot()
        from lotus.plugin_hooks import as_text
        from lotus.realtime import get_core

        user_text = as_text(kwargs.get("user_message"))
        assistant = kwargs.get("assistant_response") or ""
        if not isinstance(assistant, str):
            assistant = str(assistant)
        history = kwargs.get("conversation_history")
        if not isinstance(history, list):
            history = None
        get_core().after_turn(user_text, assistant, history=history)
    except Exception:
        logger.exception("lotus-realtime: post_llm_call failed")


def register(ctx: Any) -> None:
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("post_llm_call", _on_post_llm_call)
    logger.info("lotus-realtime: registered (unified context orchestrator)")
