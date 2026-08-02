"""lotus-profile — chart reload on session start (inject via orchestrator)."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _disabled() -> bool:
    return os.environ.get("LOTUS_PROFILE_DISABLE", "").lower() in {"1", "true", "yes", "on"}


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


def _on_session_start(**kwargs: Any) -> None:
    if _disabled():
        return
    try:
        _boot()
        from lotus.profile import get_profile

        eng = get_profile()
        eng.reload()
        logger.info(
            "lotus-profile: chart ready confidence=%s turns=%s",
            eng.profile.confidence,
            eng.profile.turn_count,
        )
    except Exception:
        logger.exception("lotus-profile: on_session_start failed")


def register(ctx: Any) -> None:
    ctx.register_hook("on_session_start", _on_session_start)
    logger.info("lotus-profile: registered (session reload; inject via orchestrator)")
