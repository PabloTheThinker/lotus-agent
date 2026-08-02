"""Paths for the L.O.T.U.S. compounding mission system."""

from __future__ import annotations

from pathlib import Path

from lotus.realtime.paths import core_dir, hermes_home

__all__ = ["core_dir", "hermes_home", "compound_json_path", "compound_md_path"]


def compound_json_path() -> Path:
    return core_dir() / "compound.json"


def compound_md_path() -> Path:
    return core_dir() / "COMPOUND.md"
