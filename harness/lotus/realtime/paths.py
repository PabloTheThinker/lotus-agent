"""Persistence paths for the L.O.T.U.S. real-time core."""

from __future__ import annotations

import os
from pathlib import Path


def hermes_home() -> Path:
    raw = os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes" / "profiles" / "lotus")
    return Path(raw).expanduser()


def core_dir() -> Path:
    d = hermes_home() / "memories" / "lotus-core"
    d.mkdir(parents=True, exist_ok=True)
    return d


def living_model_path() -> Path:
    return core_dir() / "living_model.json"


def research_log_path() -> Path:
    return core_dir() / "research_log.jsonl"


def insights_md_path() -> Path:
    return core_dir() / "INSIGHTS.md"


def approaches_md_path() -> Path:
    return core_dir() / "APPROACHES.md"
