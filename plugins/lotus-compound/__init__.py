"""lotus-compound — mission post-hooks (pre inject via orchestrator)."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, List

logger = logging.getLogger(__name__)


def _disabled() -> bool:
    return os.environ.get("LOTUS_COMPOUND_DISABLE", "").lower() in {"1", "true", "yes", "on"}


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
    from lotus.compound import get_compound

    return get_compound()


def _on_session_start(**kwargs: Any) -> None:
    if _disabled():
        return
    try:
        _engine().reload()
    except Exception:
        logger.exception("lotus-compound: on_session_start failed")


def _on_post_llm_call(**kwargs: Any) -> None:
    if _disabled():
        return
    try:
        _boot()
        from lotus.plugin_hooks import as_text, harness_owns_turn, is_crisis, living_snapshot

        if harness_owns_turn():
            return
        user_text = as_text(kwargs.get("user_message"))
        assistant = kwargs.get("assistant_response") or ""
        if not isinstance(assistant, str):
            assistant = str(assistant)
        affect, protocols = living_snapshot()
        moment_ids: List[str] = []
        try:
            from lotus.moments import get_moments

            moment_ids = [m.id for m in get_moments().graph.moments[-5:]]
        except Exception:
            pass
        _engine().after_turn(
            user_text,
            assistant,
            protocols=protocols,
            affect=affect,
            crisis=is_crisis(user_text, affect),
            moment_ids=moment_ids,
        )
    except Exception:
        logger.exception("lotus-compound: post_llm_call failed")


def register(ctx: Any) -> None:
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("post_llm_call", _on_post_llm_call)
    logger.info("lotus-compound: registered (post; inject via orchestrator)")
