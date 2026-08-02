from __future__ import annotations

from pathlib import Path

from ..realtime.paths import core_dir, hermes_home


def continuity_path() -> Path:
    return core_dir() / "continuity.json"


def resume_card_path() -> Path:
    return core_dir() / "RESUME.md"


def memory_sync_path() -> Path:
    return core_dir() / "MEMORY_SYNC.md"


def hermes_user_md() -> Path:
    return hermes_home() / "memories" / "USER.md"


def hermes_memory_md() -> Path:
    return hermes_home() / "memories" / "MEMORY.md"
