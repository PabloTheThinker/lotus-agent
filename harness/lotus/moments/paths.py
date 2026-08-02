"""Paths for the L.O.T.U.S. moments connection graph."""

from __future__ import annotations

from pathlib import Path

from lotus.realtime.paths import core_dir, hermes_home

__all__ = ["core_dir", "hermes_home", "moments_json_path", "moments_md_path"]


def moments_json_path() -> Path:
    return core_dir() / "moments.json"


def moments_md_path() -> Path:
    return core_dir() / "MOMENTS.md"
