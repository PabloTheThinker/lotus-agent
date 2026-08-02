"""Shared Hermes profile bootstrap — keep plugins thin (Hermes pattern)."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable, Optional


def hermes_home() -> Path:
    raw = os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes" / "profiles" / "lotus")
    return Path(raw).expanduser()


def ensure_harness_on_path(extra: Optional[Iterable[Path]] = None) -> Path:
    """Insert the lotus harness directory on sys.path; return the path used."""
    here_candidates = []
    if extra:
        here_candidates.extend(extra)
    # Common layouts: repo/plugins/<name>/ → repo/harness
    # profile/plugins/<name>/ → profile/harness
    here_candidates.extend(
        [
            hermes_home() / "harness",
            Path.home() / "Projects" / "lotus-agent" / "harness",
        ]
    )
    # Walk from caller-ish roots if provided via LOTUS_REPO
    repo = os.environ.get("LOTUS_REPO")
    if repo:
        here_candidates.insert(0, Path(repo).expanduser() / "harness")

    for path in here_candidates:
        path = Path(path)
        if path.is_dir() and (path / "lotus").is_dir():
            sp = str(path)
            if sp not in sys.path:
                sys.path.insert(0, sp)
            return path

    # Last resort: relative to this file (harness/lotus/plugin_bootstrap.py)
    local = Path(__file__).resolve().parents[1]
    if local.is_dir():
        sp = str(local)
        if sp not in sys.path:
            sys.path.insert(0, sp)
        return local
    raise ImportError("Could not locate L.O.T.U.S. harness package")


def bootstrap_from_plugin_file(plugin_init: Path) -> Path:
    """Bootstrap using a plugin's __init__.py path (parents[2]/harness)."""
    plugin_init = Path(plugin_init).resolve()
    candidates = [
        plugin_init.parents[2] / "harness",
        plugin_init.parents[1] / "harness",
        hermes_home() / "harness",
    ]
    return ensure_harness_on_path(candidates)
