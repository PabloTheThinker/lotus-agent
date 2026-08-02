"""Export / wipe lotus-core state — user agency over companion memory."""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from lotus.realtime.paths import core_dir, hermes_home

# Files that hold personal companion state (JSON + derived markdown / logs).
CORE_STATE_NAMES = (
    "living_model.json",
    "continuity.json",
    "moments.json",
    "compound.json",
    "profile.json",
    "prefs.json",
    "research_log.jsonl",
    "INSIGHTS.md",
    "APPROACHES.md",
    "RESUME.md",
    "MEMORY_SYNC.md",
    "MOMENTS.md",
    "COMPOUND.md",
    "PROFILE.md",
    "LOTUS_NOTES.md",
    "VOICE.md",
)


def list_core_files(*, include_missing: bool = False) -> List[Path]:
    root = core_dir()
    out: List[Path] = []
    for name in CORE_STATE_NAMES:
        path = root / name
        if include_missing or path.exists():
            out.append(path)
    # Also include any extra json/md/jsonl the user or pulse wrote
    if root.is_dir():
        for path in sorted(root.iterdir()):
            if path.is_file() and path not in out:
                if path.suffix.lower() in {".json", ".md", ".jsonl"}:
                    out.append(path)
    return out


def export_core(
    dest: Optional[Path] = None,
    *,
    keep_prefs: bool = False,
) -> Path:
    """Zip lotus-core into ``dest`` (default: timestamped zip next to profile)."""
    root = core_dir()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if dest is None:
        dest = hermes_home() / f"lotus-core-export-{stamp}.zip"
    else:
        dest = Path(dest).expanduser()
        if dest.is_dir():
            dest = dest / f"lotus-core-export-{stamp}.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)

    files = list_core_files()
    if keep_prefs:
        files = [p for p in files if p.name != "prefs.json"]

    manifest = {
        "exported_at": stamp,
        "hermes_home": str(hermes_home()),
        "core_dir": str(root),
        "files": [p.name for p in files if p.is_file()],
        "note": "L.O.T.U.S. companion state export — handle as sensitive personal data.",
    }

    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
        for path in files:
            if path.is_file():
                zf.write(path, arcname=path.name)
    return dest


def wipe_core(
    *,
    keep_prefs: bool = False,
    keep_approaches: bool = False,
) -> Tuple[int, List[str]]:
    """Delete lotus-core personal state. Returns (removed_count, names)."""
    removed: List[str] = []
    root = core_dir()
    for path in list_core_files():
        if keep_prefs and path.name == "prefs.json":
            continue
        if keep_approaches and path.name in {"APPROACHES.md", "research_log.jsonl"}:
            continue
        if path.is_file():
            path.unlink()
            removed.append(path.name)
    # Reset in-process caches so next turn does not reuse wiped memory
    _reset_engines()
    # Ensure directory still exists for future writes
    root.mkdir(parents=True, exist_ok=True)
    return len(removed), removed


def _reset_engines() -> None:
    """Drop in-process singletons without reconstructing (avoids rewriting wiped files)."""
    try:
        import lotus.realtime.core as realtime_core

        with realtime_core._LOCK:
            realtime_core._CORE = None
    except Exception:
        pass
    try:
        import lotus.continuity.engine as continuity_engine

        continuity_engine._ENGINE = None
    except Exception:
        pass
    try:
        import lotus.moments.engine as moments_engine

        moments_engine._ENGINE = None
    except Exception:
        pass
    try:
        import lotus.compound.engine as compound_engine

        compound_engine._ENGINE = None
    except Exception:
        pass
    try:
        import lotus.profile.engine as profile_engine

        profile_engine._ENGINE = None
    except Exception:
        pass
    try:
        import lotus.prefs as prefs_mod

        with prefs_mod._LOCK:
            prefs_mod._PREFS = None
    except Exception:
        pass


def summarize_core() -> dict:
    files = [p for p in list_core_files() if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    return {
        "core_dir": str(core_dir()),
        "file_count": len(files),
        "bytes": total,
        "files": [p.name for p in files],
    }


def iter_sensitive_names() -> Iterable[str]:
    return CORE_STATE_NAMES
