"""lotus-safety — output transform; crisis context owned by orchestrator."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _disabled() -> bool:
    return os.environ.get("LOTUS_SAFETY_DISABLE", "").lower() in {"1", "true", "yes", "on"}


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


def _on_transform_llm_output(**kwargs: Any) -> Optional[str]:
    if _disabled():
        return None
    text = kwargs.get("response_text")
    if not isinstance(text, str) or not text.strip():
        return None
    try:
        _boot()
        from lotus.guardrails import SAFE_REFUSAL, is_unsafe_output

        if is_unsafe_output(text):
            logger.error("lotus-safety: blocked unsafe model output")
            return SAFE_REFUSAL
    except Exception:
        logger.exception("lotus-safety: transform failed")
    return None


def register(ctx: Any) -> None:
    ctx.register_hook("transform_llm_output", _on_transform_llm_output)
    logger.info("lotus-safety: registered (output filter; crisis via orchestrator)")
