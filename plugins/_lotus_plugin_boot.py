"""Tiny shared boot helper copied beside plugins (no harness import at load)."""

from __future__ import annotations

import sys
from pathlib import Path


def boot(plugin_file: str) -> None:
    here = Path(plugin_file).resolve()
    for candidate in (
        here.parents[2] / "harness",
        Path.home() / ".hermes" / "profiles" / "lotus" / "harness",
    ):
        if (candidate / "lotus").is_dir():
            sp = str(candidate)
            if sp not in sys.path:
                sys.path.insert(0, sp)
            break
    from lotus.plugin_bootstrap import bootstrap_from_plugin_file

    bootstrap_from_plugin_file(here)
