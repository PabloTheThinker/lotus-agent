"""Paths for the internal user profile + Lotus notes."""

from __future__ import annotations

from pathlib import Path

from lotus.realtime.paths import core_dir, hermes_home

__all__ = [
    "core_dir",
    "hermes_home",
    "profile_json_path",
    "profile_md_path",
    "lotus_notes_path",
]


def profile_json_path() -> Path:
    return core_dir() / "profile.json"


def profile_md_path() -> Path:
    return core_dir() / "PROFILE.md"


def lotus_notes_path() -> Path:
    return core_dir() / "LOTUS_NOTES.md"
