"""lotus-moments — graph post-hooks (pre inject via orchestrator)."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _disabled() -> bool:
    return os.environ.get("LOTUS_MOMENTS_DISABLE", "").lower() in {"1", "true", "yes", "on"}


def _boot():
    here = Path(__file__).resolve()
    for candidate in (here.parents[2] / "harness", Path.home() / ".hermes" / "profiles" / "lotus" / "harness"):
        if (candidate / "lotus").is_dir():
            sp = str(candidate)
            if sp not in sys.path:
                sys.path.insert(0, sp)
            break
    from lotus.plugin_bootstrap import bootstrap_from_plugin_file

    bootstrap_from_plugin_file(here)


def _engine():
    _boot()
    from lotus.moments import get_moments

    return get_moments()


def _on_session_start(**kwargs: Any) -> None:
    if _disabled():
        return
    try:
        _engine().reload()
    except Exception:
        logger.exception("lotus-moments: on_session_start failed")


def _on_post_llm_call(**kwargs: Any) -> None:
    if _disabled():
        return
    try:
        _boot()
        from lotus.plugin_hooks import as_text, living_snapshot

        user_text = as_text(kwargs.get("user_message"))
        assistant = kwargs.get("assistant_response") or ""
        if not isinstance(assistant, str):
            assistant = str(assistant)
        history = kwargs.get("conversation_history")
        if not isinstance(history, list):
            history = None
        affect, protocols = living_snapshot()
        _engine().after_turn(
            user_text,
            assistant,
            session_id=str(kwargs.get("session_id") or ""),
            protocols=protocols,
            affect=affect,
            history=history,
        )
    except Exception:
        logger.exception("lotus-moments: post_llm_call failed")


def _on_session_end(**kwargs: Any) -> None:
    if _disabled():
        return
    try:
        _engine().on_session_end()
    except Exception:
        logger.exception("lotus-moments: on_session_end failed")


def register(ctx: Any) -> None:
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("post_llm_call", _on_post_llm_call)
    ctx.register_hook("on_session_end", _on_session_end)
    logger.info("lotus-moments: registered (post/session; inject via orchestrator)")
